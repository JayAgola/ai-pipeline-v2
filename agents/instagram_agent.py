"""
Instagram Agent — posts images with captions to Instagram Business accounts.
Part of the AI Content Pipeline v2.
"""
from instagram_poster import post_image_to_instagram, upload_image_to_supabase
from core.logger import get_logger
from core.errors import PipelineError

logger = get_logger("instagram_agent")

class InstagramAgent:
    """Posts content to Instagram via Meta Graph API."""

    def __init__(self, account_id: str):
        self.account_id = account_id
        logger.info(f"InstagramAgent initialised for account: {account_id}")

    def post(
        self,
        local_image_path: str,
        caption: str
    ) -> dict:
        """Upload image to Supabase and post to Instagram."""
        logger.info(f"Posting to Instagram: {caption[:40]}...")

        try:
            # Upload image to get public URL
            image_url = upload_image_to_supabase(local_image_path)

            # Post to Instagram
            result = post_image_to_instagram(
                image_url=image_url,
                caption=caption,
                ig_account_id=self.account_id
            )
            logger.info(f"Posted successfully: {result['permalink']}")
            return result

        except Exception as e:
            logger.error(f"Instagram post failed: {e}")
            raise PipelineError(f"Instagram posting failed: {e}") from e