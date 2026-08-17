import requests
from pathlib import Path

from core.config import PEXELS_API_KEY
from core.logger import get_logger

logger = get_logger("pexels")

PEXELS_URL = "https://api.pexels.com/videos/search"


class PexelsAgent:

    def __init__(self):
        self.headers = {
            "Authorization": PEXELS_API_KEY
        }

    def download_video(self, query: str, output_path: str):

        response = requests.get(
            PEXELS_URL,
            headers=self.headers,
            params={
                "query": query,
                "per_page": 1
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        if not data["videos"]:
            return None

        video = data["videos"][0]

        file_url = video["video_files"][0]["link"]

        video_bytes = requests.get(file_url).content

        output = Path(output_path)

        output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        output.write_bytes(video_bytes)

        logger.info(f"Downloaded {query}")

        return output.name
    