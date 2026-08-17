# core/pipeline_config.py

from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """
    Central configuration for the entire AI video pipeline.

    Every agent reads what it needs from this object instead of
    passing dozens of arguments around.
    """

    # Required
    topic: str

    # Script
    style: str = "educational"

    # Voice
    voice: str = "indian_male"
    voice_provider: str = "edge"

    # Research / RAG
    use_research: bool = False
    use_knowledge_base: bool = True

    # Visuals
    use_ai_visuals: bool = False

    # Distribution
    upload_to_youtube: bool = False
    post_to_instagram: bool = False

    # Branding
    channel_name: str = "AI Business Insights"

    # Video

    fps: int = 30
    width: int = 1920
    height: int = 1080

    # Timing

    title_duration: int = 90
    outro_duration: int = 60

    # Rendering

    remotion_composition: str = "AIVideoTemplate"

    # Assets

    audio_file: str = "voice.mp3"

    public_folder: str = "video/public"

    # AI visuals

    visual_aspect_ratio: str = "16:9"

    visual_style: str = (
        "cinematic, realistic, high quality, smooth camera motion"
    )

    # Future flags

    save_script: bool = True
    save_thumbnail: bool = True