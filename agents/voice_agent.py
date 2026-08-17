from pathlib import Path
from elevenlabs.client import ElevenLabs
from elevenlabs import save,VoiceSettings
from core.config import ELEVENLABS_API_KEY, VOICE_IDS, DEFAULT_VOICE, VOICE_FILE,EDGE_VOICES
from core.logger import get_logger
from core.errors import VoiceGenerationError,QuotaExceededError,ConfigError
from core.errors import retry
import asyncio
import edge_tts
from pydub import AudioSegment

logger = get_logger("voice_agent")

class VoiceAgent:
    """Converts text scripts to MP3 audio using ElevenLabs."""

    def __init__(self):
        if not ELEVENLABS_API_KEY:
            raise ConfigError("ELEVENLABS_API_KEY not set")
        self.client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        logger.info("VoiceAgent initialised")

    def _clean_audio(
        self,
        raw_path: Path,
        final_path: Path,
    ):

        audio = AudioSegment.from_file(raw_path)

        audio = audio.normalize()

        audio = audio.fade_in(150)

        audio = audio.fade_out(300)

        audio.export(
            final_path,
            format="mp3",
            bitrate="192k",
        )

        return final_path


    async def _generate_edge(
        self,
        text: str,
        voice: str,
        output_path: Path,
        rate="+5%",
        pitch="+0Hz",
    ):

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )

        await communicate.save(str(output_path))

    @retry(max_attempts=3, delay=2.0, exceptions=(Exception,))
    def generate(
        self,
        text: str,
        voice_name: str = DEFAULT_VOICE,
        provider: str = "edge",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        output_path: Path = VOICE_FILE,
    ) -> Path:
        """
        Generate voice audio from text.

        Returns:
            Path to the saved MP3 file
        """
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        if provider.lower() == "edge":

            voice = EDGE_VOICES.get(voice_name)

            if not voice:

                raise VoiceGenerationError(
                    f"Unknown Edge voice: {voice_name}"
                )

            raw_path = output_path.with_name(
                output_path.stem + "_raw.mp3"
            )

            logger.info(
                f"Generating Edge TTS voice: {voice_name}"
            )

            asyncio.run(
                self._generate_edge(
                    text=text,
                    voice=voice,
                    output_path=raw_path,
                )
            )

            self._clean_audio(
                raw_path,
                output_path,
            )

            if raw_path.exists():
                raw_path.unlink()

            logger.info(
                f"Edge voice saved: {output_path}"
            )

            return output_path
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
            logger.error(e)

            if "quota" in str(e).lower():

                logger.warning(
                    "Quota exceeded. Falling back to Edge-TTS."
                )

                return self.generate(
                    text=text,
                    voice_name="indian_male",
                    provider="edge",
                    output_path=output_path,
                )
            raise VoiceGenerationError(str(e)) from e