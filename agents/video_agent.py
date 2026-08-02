import json
import subprocess
from pathlib import Path
from core.config import VIDEO_DIR, OUTPUT_VIDEO, VIDEO_FPS, VIDEO_WIDTH, VIDEO_HEIGHT
from core.logger import get_logger
from core.errors import VideoRenderError
from core.errors import retry

logger = get_logger("video_agent")

class VideoAgent:
    """Renders animated videos using Remotion."""

    @retry(max_attempts=3, delay=2.0, exceptions=(Exception,))
    def render(
        self,
        title: str,
        subtitle: str,
        points: list,
        channel_name: str = "AI Business Insights",
        audio_file: str = "voice.mp3"
    ) -> Path:
        """Render a video and return the output path."""
        duration = 90 + (len(points) * 40 + 60) + 60
        props = {
            "title": title,
            "subtitle": subtitle,
            "points": points,
            "channelName": channel_name,
            "audioFile": audio_file
        }

        cmd = [
            "npx", "remotion", "render",
            "AIVideoTemplate",
            str(OUTPUT_VIDEO.resolve()),
            "--props", json.dumps(props),
            "--duration-in-frames", str(duration),
            "--fps", str(VIDEO_FPS),
            "--width", str(VIDEO_WIDTH),
            "--height", str(VIDEO_HEIGHT),
        ]

        logger.info(f"Rendering: '{title}' ({duration} frames)")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(VIDEO_DIR.resolve()),
                capture_output=True,
                text=True,
                timeout=600
            )
            if result.returncode != 0:
                raise VideoRenderError(result.stderr[-500:])

            logger.info(f"Render complete: {OUTPUT_VIDEO}")
            return OUTPUT_VIDEO

        except subprocess.TimeoutExpired:
            raise VideoRenderError("Render timed out after 10 minutes")
        except VideoRenderError:
            raise
        except Exception as e:
            raise VideoRenderError(str(e)) from e