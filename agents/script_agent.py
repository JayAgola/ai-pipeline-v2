import json

from langchain_groq import ChatGroq

from core.config import GROQ_API_KEY
from core.logger import get_logger
from core.errors import (
    ConfigError,
    ScriptGenerationError,
    retry,
)
from agents.multi_agent_pipeline import run_multi_agent_pipeline

logger = get_logger("script_agent")


class ScriptAgent:
    """Generates structured video scripts using Groq LLM."""

    def __init__(
        self,
        model: str = "llama-3.1-8b-instant",
        use_research: bool = False,
    ):
        if not GROQ_API_KEY:
            raise ConfigError("GROQ_API_KEY not set")

        self.use_research = use_research
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model=model,
        )

        logger.info(
            f"ScriptAgent initialized with model: {model} "
            f"(research={use_research})"
        )

    @retry(max_attempts=3, delay=2.0, exceptions=(Exception,))
    def generate(self, topic: str, style: str = "educational") -> dict:
        """
        Generate a structured video script.

        Returns:
            dict with keys:
                - title
                - subtitle
                - script
                - points
                - channel_name
        """

        # ---------- Premium Research Pipeline ----------
        if self.use_research:
            logger.info("Using multi-agent research pipeline...")

            try:
                result = run_multi_agent_pipeline(topic)

                if result.get("script_data"):
                    return result["script_data"]

                logger.warning(
                    "Multi-agent pipeline returned no script. "
                    "Falling back to single-agent generation."
                )

            except Exception as e:
                logger.warning(
                    f"Multi-agent pipeline failed: {e}. "
                    "Falling back to single-agent generation."
                )

        # ---------- Single-Agent Fallback ----------
        logger.info(f"Generating script for topic: '{topic}'")

        prompt = f"""
Write a 30-second {style} video script about: {topic}

Return ONLY valid JSON with these exact fields:

{{
  "title": "video title (max 60 chars)",
  "subtitle": "subtitle (max 80 chars)",
  "script": "full narration script (50-80 words)",
  "points": [
    "bullet point 1",
    "bullet point 2",
    "bullet point 3"
  ],
  "channel_name": "AI Business Insights"
}}

No markdown.
No backticks.
Only JSON.
"""

        try:
            response = self.llm.invoke(prompt)
            raw = response.content.strip()

            # Remove accidental markdown fences
            if raw.startswith("```"):
                raw = raw.replace("```json", "").replace("```", "").strip()

            result = json.loads(raw)

            logger.info(
                f"Script generated: '{result.get('title', 'Untitled')}'"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}")
            logger.debug(f"Raw LLM output: {raw[:500]}")

            raise ScriptGenerationError(
                f"LLM returned invalid JSON for topic '{topic}'"
            ) from e

        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            raise ScriptGenerationError(str(e)) from e