import requests
import io
import sys
import time
from pathlib import Path

from core.config import PEXELS_API_KEY
from core.logger import get_logger

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

logger = get_logger("pexels")

PEXELS_URL = "https://api.pexels.com/videos/search"

# Minimum quality requirements
MIN_WIDTH = 1280       # at least 720p
MIN_HEIGHT = 720
MIN_DURATION = 5       # at least 5 seconds
MAX_DURATION = 30      # not too long
PREFERRED_WIDTH = 1920 # prefer 1080p


class PexelsAgent:

    def __init__(self):
        self.headers = {
            "Authorization": PEXELS_API_KEY
        }
        # Track used video IDs to avoid duplicates across points
        self._used_ids: set = set()

    def _pick_best_file(self, video_files: list) -> dict | None:
        """
        Pick the best video file from available formats.
        Priority: 1920x1080 HD > 1280x720 > anything else
        Rejects vertical videos (portrait orientation).
        """
        hd_files = []
        acceptable_files = []

        for f in video_files:
            w = f.get("width", 0)
            h = f.get("height", 0)

            # Skip vertical/portrait videos
            if h > w:
                continue

            # Skip if below minimum resolution
            if w < MIN_WIDTH or h < MIN_HEIGHT:
                continue

            if w >= PREFERRED_WIDTH:
                hd_files.append(f)
            else:
                acceptable_files.append(f)

        # Return best available — prefer 1080p, fallback to 720p
        if hd_files:
            # Among HD files, pick the one closest to 1920 width
            return sorted(hd_files, key=lambda f: abs(f.get("width", 0) - PREFERRED_WIDTH))[0]
        if acceptable_files:
            return sorted(acceptable_files, key=lambda f: f.get("width", 0), reverse=True)[0]

        return None  # No acceptable file found

    def _is_acceptable_video(self, video: dict) -> bool:
        """Check if video meets duration and uniqueness requirements."""
        duration = video.get("duration", 0)
        video_id = video.get("id", 0)

        if duration < MIN_DURATION or duration > MAX_DURATION:
            return False
        if video_id in self._used_ids:
            return False

        return True

    def _search_videos(self, query: str, per_page: int = 10) -> list:
        """Search Pexels and return list of videos."""
        try:
            response = requests.get(
                PEXELS_URL,
                headers=self.headers,
                params={
                    "query": query,
                    "per_page": per_page,
                    "orientation": "landscape",  # force horizontal
                    "size": "large",              # prefer larger videos
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("videos", [])
        except Exception as e:
            logger.warning(f"Pexels search failed for '{query}': {e}")
            return []

    def download_video(
        self,
        query: str,
        output_path: str,
        fallback_queries: list[str] | None = None
    ) -> str | None:
        """
        Download the best matching HD landscape video for a query.

        Args:
            query: Primary search term (should match script point)
            output_path: Where to save the .mp4 file
            fallback_queries: Try these if primary query returns no good results

        Returns:
            Filename if successful, None if failed
        """
        all_queries = [query] + (fallback_queries or [])

        for attempt_query in all_queries:
            logger.info(f"Searching Pexels: '{attempt_query}'")
            videos = self._search_videos(attempt_query, per_page=10)

            if not videos:
                logger.warning(f"No results for '{attempt_query}'")
                continue

            # Find first acceptable video with a good file format
            for video in videos:
                if not self._is_acceptable_video(video):
                    continue

                best_file = self._pick_best_file(video.get("video_files", []))
                if not best_file:
                    continue

                # Found a good one — download it
                video_id = video["id"]
                file_url = best_file["link"]
                width = best_file.get("width", "?")
                height = best_file.get("height", "?")
                duration = video.get("duration", "?")

                logger.info(
                    f"Selected video {video_id}: "
                    f"{width}x{height}, {duration}s — '{attempt_query}'"
                )

                try:
                    video_bytes = requests.get(file_url, timeout=120).content
                    output = Path(output_path)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(video_bytes)

                    # Mark as used so next point gets a different clip
                    self._used_ids.add(video_id)
                    logger.info(f"Saved: {output.name}")
                    return output.name

                except Exception as e:
                    logger.error(f"Download failed for video {video_id}: {e}")
                    continue

            logger.warning(f"No acceptable video found for '{attempt_query}'")

        logger.error(f"All queries failed for: {query}")
        return None

    def download_multiple(
        self,
        points: list[str],
        output_dir: str,
        topic: str = ""
    ) -> list[str | None]:
        """
        Download one unique HD video per script point.

        Args:
            points: List of script bullet points
            output_dir: Directory to save clips
            topic: Overall video topic (used as fallback query)

        Returns:
            List of filenames (same length as points), None where download failed
        """
        results = []
        self._used_ids.clear()  # Reset for fresh batch

        for i, point in enumerate(points):
            # Build a specific search query from the point text
            # Clean it up — remove special chars, keep key terms
            clean_point = (
                point
                .replace("→", "")
                .replace(":", "")
                .replace("-", " ")
                .strip()
            )
            # Use first 5 words for focused search
            query_words = clean_point.split()[:5]
            primary_query = " ".join(query_words)

            # Fallback: use the topic + point number
            fallback = f"{topic} business technology" if topic else "technology business"

            output_path = f"{output_dir}/clip_{i + 1:02d}.mp4"

            logger.info(f"Point {i + 1}/{len(points)}: '{primary_query}'")

            result = self.download_video(
                query=primary_query,
                output_path=output_path,
                fallback_queries=[topic, fallback, "technology"]
            )

            results.append(result)

            # Rate limiting — Pexels allows 200 requests/hour free
            # Small delay between downloads to be polite
            if i < len(points) - 1:
                time.sleep(0.5)

        successful = sum(1 for r in results if r is not None)
        logger.info(
            f"Downloaded {successful}/{len(points)} clips successfully"
        )

        return results