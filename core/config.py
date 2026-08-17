import os
from pathlib import Path

from dotenv import load_dotenv

from core.errors import ConfigError
from core.logger import get_logger

load_dotenv()

logger = get_logger("config")

# ---------------------------------------------------------------------
# Base Directories
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

VIDEO_DIR = BASE_DIR / "video"
PUBLIC_DIR = VIDEO_DIR / "public"
OUTPUT_DIR = BASE_DIR / "output"

VOICE_FILE = PUBLIC_DIR / "voice.mp3"
OUTPUT_VIDEO = OUTPUT_DIR / "final_video.mp4"

PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------
# Video Settings
# ---------------------------------------------------------------------

VIDEO_FPS = int(os.getenv("VIDEO_FPS", 30))
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", 1920))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", 1080))

# ---------------------------------------------------------------------
# Voices
# ---------------------------------------------------------------------

VOICE_IDS = {
    # ElevenLabs
    "indman": "4PouCMoXXbYvmL97v8kr",
}

EDGE_VOICES = {
    "english_male": "en-US-GuyNeural",
    "english_female": "en-US-JennyNeural",

    "indian_male": "en-IN-PrabhatNeural",
    "indian_female": "en-IN-NeerjaNeural",

    "hindi_male": "hi-IN-MadhurNeural",
    "hindi_female": "hi-IN-SwaraNeural",
}

DEFAULT_EDGE_VOICE = "hindi_female"
DEFAULT_VOICE = "hindi_female"

# ---------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

LUMA_API_KEY = os.getenv("LUMA_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

SUPABASE_URL_PGVECTOR = os.getenv("SUPABASE_URL_PGVECTOR")
SUPABASE_KEY_PGVECTOR = os.getenv("SUPABASE_KEY_PGVECTOR")

INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

DEVTO_API_KEY = os.getenv("DEVTO_API_KEY")


# ---------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------

YOUTUBE_TOKEN_FILE = BASE_DIR / "youtube_token.json"

DEFAULT_PRIVACY = "unlisted"


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def get_voice_id(name: str) -> str:
    """
    Returns ElevenLabs voice id.
    """

    return VOICE_IDS.get(name, VOICE_IDS[DEFAULT_VOICE])


def require_env(*variables: str):
    """
    Validate environment variables.
    """

    missing = []

    for variable in variables:
        if not os.getenv(variable):
            missing.append(variable)

    if missing:
        raise ConfigError(
            "Missing environment variables: "
            + ", ".join(missing)
        )


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------

def validate_config():
    """
    Validate required configuration.
    """

    require_env(
        "GROQ_API_KEY",
        "ELEVENLABS_API_KEY",
        "LUMA_API_KEY",
    )

    logger.info("Configuration loaded successfully.")