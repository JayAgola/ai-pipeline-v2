import json
import shutil
import subprocess
from pathlib import Path

from mutagen.mp3 import MP3

from core.config import (
    VIDEO_DIR,
    OUTPUT_VIDEO,
    VIDEO_FPS,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VOICE_FILE,
)
from core.errors import VideoRenderError, retry
from core.logger import get_logger

logger = get_logger("video_agent")


class VideoAgent:
    """Render videos using Remotion."""

    TITLE_DURATION = 90
    OUTRO_DURATION = 60

    @staticmethod
    def get_audio_duration_frames(mp3_path: Path, fps: int = 30) -> int:
        """
        Returns audio duration in frames.
        """

        if not mp3_path.exists():
            raise VideoRenderError(
                f"Voice file not found: {mp3_path}"
            )

        audio = MP3(str(mp3_path))

        if audio.info.length <= 0:
            raise VideoRenderError(
                "Invalid audio duration."
            )

        return max(int(audio.info.length * fps), 1)

    @staticmethod
    def validate_clip_files(clips: list[str]):
        """
        Ensure every clip exists.
        """

        for clip in clips:
            clip_path = VIDEO_DIR / "public" / clip

            if not clip_path.exists():
                raise VideoRenderError(
                    f"Missing clip: {clip_path}"
                )

    @retry(max_attempts=3, delay=2.0, exceptions=(Exception,))
    def render(
        self,
        title: str,
        subtitle: str,
        points: list[str],
        clip_files: list[str],
        channel_name: str,
        audio_file: str = "voice.mp3",
    ) -> Path:

        self.validate_clip_files(clip_files)

        duration = self.get_audio_duration_frames(
            VOICE_FILE,
            VIDEO_FPS,
        )

        if duration <= (
            self.TITLE_DURATION + self.OUTRO_DURATION
        ):
            raise VideoRenderError(
                "Audio is too short."
            )

        props = {
            "title": title,
            "subtitle": subtitle,
            "points": points,
            "clipFiles": clip_files,
            "channelName": channel_name,
            "audioFile": audio_file,
            "durationInFrames": duration,
            "titleDuration": self.TITLE_DURATION,
            "outroDuration": self.OUTRO_DURATION,
        }

        npx = shutil.which("npx")

        if npx is None:
            npx = shutil.which("npx.cmd")

        if npx is None:
            raise VideoRenderError(
                "Unable to locate npx."
            )

        output_path = OUTPUT_VIDEO.resolve()

        command = [
            npx,
            "remotion",
            "render",
            "src/index.ts",
            "AIVideoTemplate",
            str(output_path),
            "--props",
            json.dumps(props),
            "--duration-in-frames",
            str(duration),
            "--fps",
            str(VIDEO_FPS),
            "--width",
            str(VIDEO_WIDTH),
            "--height",
            str(VIDEO_HEIGHT),
        ]

        logger.info(
            f"Rendering video ({duration} frames)..."
        )

        try:
            result = subprocess.run(
                command,
                cwd=VIDEO_DIR,
                capture_output=True,
                text=True,
                timeout=900,
            )

        except subprocess.TimeoutExpired:
            raise VideoRenderError(
                "Rendering timed out."
            )

        except Exception as e:
            raise VideoRenderError(str(e))

        if result.returncode != 0:
            logger.error(result.stderr)

            raise VideoRenderError(
                f"Remotion failed.\n\n{result.stderr}"
            )

        if not output_path.exists():
            raise VideoRenderError(
                "Render finished but output file was not created."
            )

        logger.info(
            f"Video created successfully: {output_path}"
        )

        return output_path