from pathlib import Path
from elevenlabs.client import ElevenLabs
from elevenlabs import save,VoiceSettings
from core.config import ELEVENLABS_API_KEY, VOICE_IDS, DEFAULT_VOICE, VOICE_FILE
from core.logger import get_logger
from core.errors import VoiceGenerationError,QuotaExceededError,ConfigError
from core.errors import retry

logger = get_logger("voice_agent")

class VoiceAgent:
    """Converts text scripts to MP3 audio using ElevenLabs."""

    def __init__(self):
        if not ELEVENLABS_API_KEY:
            raise ConfigError("ELEVENLABS_API_KEY not set")
        self.client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        logger.info("VoiceAgent initialised")

    @retry(max_attempts=3, delay=2.0, exceptions=(Exception,))
    def generate(
        self,
        text: str,
        voice_name: str = DEFAULT_VOICE,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        output_path: Path = VOICE_FILE
    ) -> Path:
        """
        Generate voice audio from text.

        Returns:
            Path to the saved MP3 file
        """
        voice_id = VOICE_IDS.get(voice_name)
        if not voice_id:
            raise VoiceGenerationError(
                f"Unknown voice: '{voice_name}'. Available: {list(VOICE_IDS.keys())}"
            )

        char_count = len(text)
        logger.info(f"Generating voice: {voice_name} | {char_count} chars")

        try:
            # audio = self.client.text_to_speech.convert(
            #     text=text,
            #     voice=voice_id,
            #     model="eleven_multilingual_v2",
            #     voice_settings={"stability": 0.5, "similarity_boost": 0.75}
            # )
            audio = self.client.text_to_speech.convert(
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                text=text,
                voice_settings=VoiceSettings(
                    stability=stability,
                    similarity_boost=similarity_boost
                ),
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            save(audio, str(output_path))
            logger.info(f"Voice saved: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Voice generation failed: {e}")
            if "quota" in str(e).lower():
                raise QuotaExceededError(
                    "ElevenLabs quota exceeded. Wait for monthly reset."
                ) from e
            raise VoiceGenerationError(str(e)) from e