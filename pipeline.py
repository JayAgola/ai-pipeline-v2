"""
AI Video Pipeline v2
Clean, modular, production-ready.
Usage: python pipeline.py
"""
import time
from core.config import validate_config, OUTPUT_VIDEO
# from core.config import validate_config, OUTPUT_VIDEO,INSTAGRAM_ACCOUNT_ID
from core.logger import get_logger
from core.errors import PipelineError
from agents.script_agent import ScriptAgent
from agents.voice_agent import VoiceAgent
from agents.video_agent import VideoAgent 
# from agents.upload_agent import UploadAgent 
from agents.thumbnail_agent import ThumbnailAgent 
from agents.instagram_agent import InstagramAgent 
from agents.knowledge_base import ContentKnowledgeBase
from agents.visual_agent import VisualAgent
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from core.pipeline_config import PipelineConfig
from agents.pexels_agent import PexelsAgent

logger = get_logger("pipeline")
# public_dir = Path("video/public")

# for file in public_dir.glob("scene_*.mp4"):
#     file.unlink(missing_ok=True)
def _generate_single_clip(agent, prompt, index):
    clip_path = Path("video/public") / f"scene_{index}.mp4"

    agent.generate_clip(
        prompt,
        str(clip_path)
    )

    return clip_path.name

def generate_all_clips(
    visual_agent,
    prompts,
):
    """
    Generate all clips concurrently.
    """

    clip_files = [None] * len(prompts)

    with ThreadPoolExecutor(
        max_workers=min(4, len(prompts))
    ) as executor:

        futures = {
            executor.submit(
                _generate_single_clip,
                visual_agent,
                prompt,
                i,
            ): i
            for i, prompt in enumerate(prompts)
        }

        for future in as_completed(futures):

            index = futures[future]

            clip_files[index] = future.result()

    return clip_files

def run(config: PipelineConfig) -> dict:
    """Run the full multi-platform AI content pipeline."""

    results = {
    "topic": config.topic,
    "success": False,
    "platforms": {}
}

    try:
        validate_config()

        # Step 1: Script
        script_agent = ScriptAgent(
    use_research=config.use_research
)

        script_data = script_agent.generate(
            config.topic,
            style=config.style
        )
        
        results["script"] = script_data

        



        # Step 2: Voice
        voice_agent = VoiceAgent()
        audio_path = voice_agent.generate(
            text=script_data["script"],
            voice_name=config.voice,
            provider=config.voice_provider,
        )
        results["audio_path"] = str(audio_path)

        # Setp : visual Clips

        pexels = PexelsAgent()

        clip_files = []

        for i, point in enumerate(script_data["points"]):

            clip = pexels.download_video(
                point,
                f"video/public/scene_{i}.mp4"
            )

            if clip:
                clip_files.append(clip)

        # clip_files = []

        # if config.use_ai_visuals:

        #     visual_agent = VisualAgent()

        #     prompts = visual_agent.generate_scene_prompts(
        #         script_data["points"],
        #         config.topic
        #     )

        #     logger.info("Generating AI clips...")

        #     public_dir = Path("video/public")

        #     for file in public_dir.glob("scene_*.mp4"):
        #         file.unlink(missing_ok=True)

        #     try:
        #         clip_files = generate_all_clips(
        #             visual_agent,
        #             prompts,
        #         )
        #     except Exception as e:
        #         logger.warning(f"AI clip generation failed: {e}")
        #         clip_files = []
        

        # Step 3: Video
        video_agent = VideoAgent()
        # video_path = video_agent.render(
        #     title=script_data["title"],
        #     subtitle=script_data["subtitle"],
        #     points=script_data["points"],
        #     channel_name=script_data["channel_name"]
        # )
        video_path = video_agent.render(
            title=script_data["title"],
            subtitle=script_data["subtitle"],
            points=script_data["points"],
            clip_files=clip_files,
            channel_name=config.channel_name
        )
        results["video_path"] = str(video_path)

        # After step 3 (video render) succeeds:
        kb = ContentKnowledgeBase()
        kb.store_script(config.topic, script_data)
        logger.info(f"Script saved to knowledge base. Total in KB: {kb.count_total()}")

        # # Step 4: YouTube upload (optional)
        # if upload_to_youtube:
        #     logger.info("Uploading to YouTube...")

        #     upload_agent = UploadAgent()
        #     yt_result = upload_agent.upload(
        #         video_path=str(video_path),
        #         title=script_data["title"],
        #         description=f"AI-generated video about: {topic}"
        #     )

        #     results["platforms"]["youtube"] = yt_result
        #     youtube_url = yt_result.get("url", "")
        # else:
        #     youtube_url = ""

        # Step 5: Instagram post (optional)
        # if post_to_instagram:
        #     logger.info("Posting to Instagram...")

        #     # Generate thumbnail
        #     thumb_agent = ThumbnailAgent()
        #     thumb_path = thumb_agent.generate(
        #         title=script_data["title"],
        #         subtitle=script_data["subtitle"]
        #     )

        #     # Build Instagram caption
        #     caption = (
        #         f"{script_data['title']}\n\n"
        #         f"{script_data['script'][:200]}...\n\n"
        #     )

        #     if youtube_url:
        #         caption += f"Watch the full video: {youtube_url}\n\n"

        #     caption += (
        #         f"#AIcontent #automation #"
        #         f"{topic.replace(' ', '')[:20]} "
        #         f"#BuildingInPublic #AItools"
        #     )

        #     ig_agent = InstagramAgent(
        #         account_id=os.getenv("INSTAGRAM_ACCOUNT_ID")
        #     )

        #     ig_result = ig_agent.post(
        #         local_image_path=thumb_path,
        #         caption=caption
        #     )

        #     results["platforms"]["instagram"] = ig_result

        results["success"] = True

        logger.info(
            f"Pipeline complete. Platforms: "
            f"{list(results['platforms'].keys())}"
        )

        return results

    except PipelineError as e:
        logger.error(f"Pipeline error: {e}")
        results["error"] = str(e)

        return results
    

if __name__ == "__main__":
    cfg = PipelineConfig(
    topic="Top 5 mutual funds this month for Indian investors",
    voice="hindi_female",
    voice_provider="edge",
    style="educational",

    use_research=False,
    use_knowledge_base=True,
    use_ai_visuals=True,

    upload_to_youtube=False,
    post_to_instagram=True,

    channel_name="AI Business Insights",
)

    result = run(cfg)

    print("\n" + "="*40)
    if result["success"]:
        print("✅ Pipeline complete!")
        for platform, data in result.get("platforms", {}).items():
            print(f"  {platform}: {data.get('permalink') or data.get('url', 'posted')}")
    else:
        print(f"❌ Pipeline failed: {result.get('error')}")