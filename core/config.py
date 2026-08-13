import os
from pathlib import Path
from dotenv import load_dotenv
from core.logger import get_logger
from core.errors import ConfigError

load_dotenv()
logger = get_logger("config")
# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
VIDEO_DIR = BASE_DIR / "video"
PUBLIC_DIR = VIDEO_DIR / "public"
OUTPUT_DIR = BASE_DIR / "output"
VOICE_FILE = PUBLIC_DIR / "voice.mp3"
OUTPUT_VIDEO = OUTPUT_DIR / "final_video.mp4"

# Ensure directories exist
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

# ElevenLabs voice IDs
VOICE_IDS = {
    "indman": "4PouCMoXXbYvmL97v8kr",
    # "adam":   "pNInz6obpgDQGcFmaJgB",
    # "bella":  "EXAVITQu4vr4xnSDxMaL",
}
DEFAULT_VOICE = "indman"

# Video settings
VIDEO_FPS = 30
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

# YouTube settings
YOUTUBE_TOKEN_FILE = BASE_DIR / "youtube_token.json"
DEFAULT_PRIVACY = "unlisted"

# Validate required keys on startup
def validate_config():
    missing = []
    if not GROQ_API_KEY: missing.append("GROQ_API_KEY")
    if not ELEVENLABS_API_KEY: missing.append("ELEVENLABS_API_KEY")
    # Instagram is optional — only warn, don't raise
    # if not INSTAGRAM_ACCOUNT_ID:
    #     logger.warning("INSTAGRAM_ACCOUNT_ID not set — Instagram posting disabled")
    if missing:
        raise ConfigError(f"Missing required env vars: {', '.join(missing)}")