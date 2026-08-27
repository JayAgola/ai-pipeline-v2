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
from agents.knowledge_base import ContentKnowledgeBase

logger = get_logger("script_agent")


class ScriptAgent:
    """Generates structured video scripts using Groq LLM."""

    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        use_research: bool = False,
    ):
        if not GROQ_API_KEY:
            raise ConfigError("GROQ_API_KEY not set")

        self.use_research = use_research
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model=model,
        )
        self.kb = ContentKnowledgeBase()

        logger.info(
            f"ScriptAgent initialized with model: {model} "
            f"(research={use_research})"
        )

    @retry(max_attempts=3, delay=2.0, exceptions=(Exception,))
    def generate(self, topic: str, style: str = "educational" ,duration_seconds: int = 180,) -> dict:
        """
        Generate a structured video script.
        """
        target_words = int(duration_seconds * 2.5)
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

        # ---------- Knowledge Base ----------
        similar_past = self.kb.search_similar(topic, threshold=0.65)
        past_context = ""

        if similar_past:
            logger.info(f"KB: {len(similar_past)} similar scripts found")

            titles = "\n".join(
                f'- "{item["title"]}"' for item in similar_past
            )

            summaries = "\n".join(
                f'• {item["script"][:200]}...'
                for item in similar_past
            )

            past_context = f"""
    IMPORTANT — Similar videos already exist.

    Previous titles:
    {titles}

    Previous summaries:
    {summaries}

    Create a NEW angle.

    Rules:
    1. Don't repeat previous points.
    2. Find a different perspective.
    3. Mention previous coverage only if useful.
    """
        else:
            logger.info("KB: No similar content found.")

        # ---------- Prompt ----------
        prompt = f"""
You are a professional YouTube script writer.

Topic: {topic}

Target duration: {duration_seconds} seconds.

Write approximately {target_words} words.

Return ONLY JSON.

{{
"title":"...",
"subtitle":"...",
"script":"...",
"points":[
...
],
"channel_name":"AI Business Insights"
}}
"""

        try:
            response = self.llm.invoke(prompt)
            raw = response.content.strip()

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
            # Step 0: Check knowledge base for similar past content
            similar_past = self.kb.search_similar(topic, threshold=0.65)
            past_context = ""

            if similar_past:
                past_titles = [r["title"] for r in similar_past]
                past_scripts = [r["script"][:200] for r in similar_past]
                logger.info(f"KB: {len(similar_past)} similar past scripts found")

                past_context = f"""
    IMPORTANT — We have already covered similar topics:
    {chr(10).join([f'- "{t}"' for t in past_titles])}

    Brief summaries of what was covered:
    {chr(10).join([f'• {s}...' for s in past_scripts])}

    Your new script MUST:
    1. NOT repeat the same angles or key points from the above
    2. Find a DIFFERENT perspective, angle, or specific aspect of the topic
    3. Reference that this builds on previous coverage if relevant
    """
            else:
                logger.info("KB: No similar content — fresh angle, no constraints")

            # Build the generation prompt
            prompt = f"""You are a professional video script writer.

    Topic: {topic}
    Style: {style}
    {past_context}

    Write a 30-second video script. Return ONLY valid JSON:
    {{
    "title": "specific title (max 60 chars)",
    "subtitle": "subtitle (max 80 chars)",
    "script": "full narration (60-90 words)",
    "points": ["point 1", "point 2", "point 3"],
    "channel_name": "AI Business Insights",
    "is_fresh_angle": {str(len(similar_past) == 0).lower()}
    }}

    No markdown, no backticks."""

            # ... rest of existing generate() method unchanged ...
            try:
                response = self.llm.invoke(prompt)
                raw = response.content.strip()
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                result = json.loads(raw.strip())
                logger.info(f"Script generated: '{result.get('title')}'")
                return result
            except json.JSONDecodeError as e:
                raise ScriptGenerationError(f"JSON parse failed for '{topic}'") from e