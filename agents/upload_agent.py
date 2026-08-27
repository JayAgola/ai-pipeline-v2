# agents/upload_agent.py
import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from core.logger import get_logger
from core.errors import PipelineError, retry
from core.config import YOUTUBE_TOKEN_FILE

logger = get_logger("upload_agent")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

class UploadAgent:
    """Uploads rendered MP4 to YouTube via OAuth2."""

    def __init__(self):
        self.youtube = self._authenticate()

    def _authenticate(self):
        creds = None
        token_path = YOUTUBE_TOKEN_FILE

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(token_path), SCOPES
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "client_secrets.json", SCOPES
                )
                creds = flow.run_local_server(port=0)

            token_path.write_text(creds.to_json())

        return build("youtube", "v3", credentials=creds)

    @retry(max_attempts=3, delay=5.0, exceptions=(Exception,))
    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: list = None,
        privacy: str = "unlisted",
    ) -> dict:
        """Upload MP4 to YouTube. Returns video URL."""

        if not Path(video_path).exists():
            raise PipelineError(f"Video file not found: {video_path}")

        logger.info(f"Uploading to YouTube: '{title}'")

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags or ["AI", "automation"],
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5  # 5MB chunks
        )

        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Upload progress: {progress}%")

        video_id = response["id"]
        url = f"https://youtube.com/watch?v={video_id}"
        logger.info(f"Uploaded: {url}")

        return {
            "video_id": video_id,
            "url": url,
            "title": title,
            "privacy": privacy,
        }