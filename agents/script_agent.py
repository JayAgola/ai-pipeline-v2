import json
from langchain_groq import ChatGroq
from core.config import GROQ_API_KEY
from core.logger import get_logger
from core.errors import ScriptGenerationError
from core.errors import retry

logger = get_logger("script_agent")

class ScriptAgent:
    """Generates structured video scripts using Groq LLM."""

    def __init__(self, model: str = "llama-3.1-8b-instant"):
        if not GROQ_API_KEY:
            raise ConfigError("GROQ_API_KEY not set")
        self.llm = ChatGroq(api_key=GROQ_API_KEY, model=model)
        logger.info(f"ScriptAgent initialised with model: {model}")

    @retry(max_attempts=3, delay=2.0, exceptions=(Exception,))
    def generate(self, topic: str, style: str = "educational") -> dict:
        """
        Generate a structured video script for a topic.

        Returns:
            dict with keys: title, subtitle, script, points, channel_name
        """
        logger.info(f"Generating script for topic: '{topic}'")

        prompt = f"""Write a 30-second {style} video script about: {topic}

Return ONLY valid JSON with these exact fields:
{{
  "title": "video title (max 60 chars)",
  "subtitle": "subtitle (max 80 chars)",
  "script": "full narration script (50-80 words)",
  "points": ["bullet point 1", "bullet point 2", "bullet point 3"],
  "channel_name": "AI Business Insights"
}}

No markdown, no backticks, only JSON."""

        try:
            response = self.llm.invoke(prompt)
            raw = response.content.strip()

            # Clean any accidental markdown
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            result = json.loads(raw)
            logger.info(f"Script generated: '{result.get('title', 'untitled')}'")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}")
            logger.debug(f"Raw LLM output: {raw[:200]}")
            raise ScriptGenerationError(
                f"LLM returned invalid JSON for topic '{topic}'"
            ) from e
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            raise ScriptGenerationError(str(e)) from e