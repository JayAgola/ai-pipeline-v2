"""
Content Knowledge Base
Stores past scripts as vector embeddings so agents can reference
previous content before writing new scripts.
Uses Supabase pgvector + sentence-transformers (both free).
"""
import os
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from supabase import create_client
from core.logger import get_logger
from core.config import SUPABASE_URL_PGVECTOR,SUPABASE_KEY_PGVECTOR
logger = get_logger("knowledge_base")

# Free local embeddings — no API cost
embedder = SentenceTransformer("all-MiniLM-L6-v2")

supabase = create_client(
    SUPABASE_URL_PGVECTOR,
    SUPABASE_KEY_PGVECTOR
)

class ContentKnowledgeBase:
    """
    Vector database of past scripts.
    Agents query this before writing to avoid repetition.
    """

    def search_similar(
        self,
        topic: str,
        threshold: float = 0.7,
        max_results: int = 3
    ) -> list:
        """
        Find past scripts similar to the new topic.
        Returns list of similar past content, or empty list if none found.
        """
        logger.info(f"Searching KB for similar content: '{topic[:40]}'")
        query_embedding = embedder.encode(topic).tolist()

        try:
            results = supabase.rpc("match_past_content", {
                "query_embedding": query_embedding,
                "match_count": max_results,
                "match_threshold": threshold
            }).execute()

            if results.data:
                logger.info(f"Found {len(results.data)} similar past scripts")
                for r in results.data:
                    logger.info(
                        f"  Similarity {r['similarity']:.2f}: '{r['title']}'"
                    )
            else:
                logger.info("No similar past content found — fresh topic")

            return results.data or []

        except Exception as e:
            logger.warning(f"KB search failed: {e}")
            return []

    def store_script(self, topic: str, script_data: dict) -> bool:
        """
        Store a new script in the knowledge base after it's approved.
        Call this AFTER a video is approved — not before.
        """
        logger.info(f"Storing script in KB: '{script_data.get('title', topic)}'")

        # Embed the combined topic + script for richer matching
        text_to_embed = f"{topic} {script_data.get('script', '')}"
        embedding = embedder.encode(text_to_embed).tolist()

        try:
            supabase.table("content_kb").insert({
                "topic": topic,
                "title": script_data.get("title", ""),
                "script": script_data.get("script", ""),
                "points": json.dumps(script_data.get("points", [])),
                "embedding": embedding,
                "channel_name": script_data.get("channel_name", "")
            }).execute()

            logger.info("Script stored in KB [OK]")
            return True

        except Exception as e:
            logger.error(f"Failed to store in KB: {e}")
            return False

    def get_similar_titles(self, topic: str) -> list:
        """Quick check — just returns titles of similar past scripts."""
        similar = self.search_similar(topic, threshold=0.6)
        return [r["title"] for r in similar]

    def count_total(self) -> int:
        """How many scripts are in the knowledge base."""
        try:
            result = supabase.table("content_kb").select("id", count="exact").execute()
            return result.count or 0
        except:
            return 0