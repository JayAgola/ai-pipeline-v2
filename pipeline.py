"""
AI Video Pipeline v2
Clean, modular, production-ready.
Usage: python pipeline.py
"""
import time
from core.config import validate_config, OUTPUT_VIDEO
from core.logger import get_logger
from core.errors import PipelineError
from agents.script_agent import ScriptAgent
from agents.voice_agent import VoiceAgent

logger = get_logger("pipeline")

def run(
    topic: str,
    voice: str = "indman",
    style: str = "educational",
    upload_to_youtube: bool = False
) -> dict:
    """
    Run the full AI video pipeline.


    Args:
        topic: The video topic
        voice: Voice name (rachel/adam/bella)
        style: Script style (educational/conversational/news)
        upload_to_youtube: Whether to auto-upload after render


    Returns:
        dict with pipeline results
    """
    start_time = time.time()
    logger.info("=" * 50)
    logger.info(f"PIPELINE START: '{topic}'")
    logger.info("=" * 50)

    results = {"topic": topic, "success": False}

    try:
        # Validate config first
        validate_config()

        # Step 1: Generate script
        logger.info("Step 1/3 — Generating script...")
        script_agent = ScriptAgent()
        script_data = script_agent.generate(topic, style=style)
        results["script"] = script_data
        logger.info(f"Script: '{script_data['title']}'")

        # Step 2: Generate voice
        logger.info("Step 2/3 — Generating voice...")
        voice_agent = VoiceAgent()
        audio_path = voice_agent.generate(
            text=script_data["script"],
            voice_name=voice
        )
        results["audio_path"] = str(audio_path)

        # Step 3: Render video (calls Remotion via subprocess)
        logger.info("Step 3/3 — Rendering video (this takes 3-5 min)...")
        # VideoAgent import here to avoid loading it if voice fails
        from agents.video_agent import VideoAgent
        video_agent = VideoAgent()
        video_path = video_agent.render(
            title=script_data["title"],
            subtitle=script_data["subtitle"],
            points=script_data["points"],
            channel_name=script_data["channel_name"]
        )
        results["video_path"] = str(video_path)

        # Optional: Upload to YouTube
        if upload_to_youtube:
            logger.info("Uploading to YouTube...")
            from agents.upload_agent import UploadAgent
            upload_agent = UploadAgent()
            upload_result = upload_agent.upload(
                video_path=str(video_path),
                title=script_data["title"],
                description=f"AI-generated video about: {topic}"
            )
            results["youtube"] = upload_result

        elapsed = round(time.time() - start_time, 1)
        results["success"] = True
        results["elapsed_seconds"] = elapsed

        logger.info("=" * 50)
        logger.info(f"PIPELINE COMPLETE in {elapsed}s")
        logger.info(f"Output: {video_path}")
        logger.info("=" * 50)

        return results

    except PipelineError as e:
        logger.error(f"Pipeline failed: {type(e).__name__}: {e}")
        results["error"] = str(e)
        results["error_type"] = type(e).__name__
        return results

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        results["error"] = str(e)
        return results


if __name__ == "__main__":
    result = run(
        topic="Top 3 AI tools every Indian entrepreneur should use in 2025",
        voice="indman",
        style="educational",
        upload_to_youtube=False  # set True when ready to upload
    )

    if result["success"]:
        print(f"\n✅ Done! Video: {result['video_path']}")
    else:
        print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")
