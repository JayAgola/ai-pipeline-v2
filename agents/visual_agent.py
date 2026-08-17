"""
Visual Agent
Generates AI video clips for each script point using Luma Dream Machine.
"""

import os
import time
from pathlib import Path

import requests
from core.config import LUMA_API_KEY
from core.errors import PipelineError
from core.logger import get_logger

logger = get_logger("visual_agent")

LUMA_API_KEY = LUMA_API_KEY
LUMA_BASE_URL = "https://agents.lumalabs.ai/v1"


class VisualAgent:
    """Generate AI video clips."""

    POLL_INTERVAL = 5          # seconds
    MAX_POLLS = 60             # 5 minutes
    REQUEST_TIMEOUT = 60       # seconds

    def __init__(self):
        if not LUMA_API_KEY:
            raise PipelineError(
                "LUMA_API_KEY is missing."
            )

        self.headers = {
            "Authorization": f"Bearer {LUMA_API_KEY}",
            "Content-Type": "application/json",
        }

    def generate_scene_prompts(
        self,
        points: list[str],
        topic: str,
    ) -> list[str]:
        """
        Convert bullet points into cinematic prompts.
        """

        prompts = []

        for point in points:
            prompts.append(
                (
                    f"Cinematic realistic b-roll of {point}. "
                    f"Topic: {topic}. "
                    "Ultra realistic, professional lighting, "
                    "smooth camera movement, 4K quality, "
                    "high detail, documentary style, "
                    "no text, no captions, no watermark."
                )
            )

        return prompts

    def generate_clip(
        self,
        prompt: str,
        output_path: str,
    ) -> str:
        """
        Generate one AI clip.
        """

        logger.info(
            f"Generating clip: {prompt[:80]}..."
        )

        response = requests.post(
            f"{LUMA_BASE_URL}/generations",
            headers=self.headers,
            json={
                "prompt": prompt,
                "aspect_ratio": "16:9",
            },
            timeout=self.REQUEST_TIMEOUT,
        )

        print("=" * 80)
        print("Status:", response.status_code)
        print("Response:")
        print(response.text)
        print("=" * 80)

        response.raise_for_status()

        generation = response.json()

        generation_id = generation["id"]

        logger.info(
            f"Generation ID: {generation_id}"
        )

        video_url = self._wait_for_generation(
            generation_id
        )

        self._download_video(
            video_url,
            output_path,
        )

        logger.info(
            f"Saved clip -> {output_path}"
        )

        return output_path

    def _wait_for_generation(
        self,
        generation_id: str,
    ) -> str:
        """
        Poll until generation finishes.
        """

        url = (
            f"{LUMA_BASE_URL}/generations/"
            f"{generation_id}"
        )

        for _ in range(self.MAX_POLLS):

            time.sleep(self.POLL_INTERVAL)

            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            data = response.json()

            state = data.get("state")

            if state == "completed":
                return data["assets"]["video"]

            if state == "failed":
                raise PipelineError(
                    "Luma generation failed."
                )

            logger.info(
                f"Generation status: {state}"
            )

        raise PipelineError(
            "Generation timed out."
        )

    def _download_video(
        self,
        video_url: str,
        output_path: str,
    ):
        """
        Download generated clip.
        """

        response = requests.get(
            video_url,
            timeout=self.REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        output = Path(output_path)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_bytes(response.content)

        if not output.exists():
            raise PipelineError(
                "Video download failed."
            )

        if output.stat().st_size == 0:
            raise PipelineError(
                "Downloaded video is empty."
            )