"""
AI SEO Blog Agent
Keyword → web research → structured blog post → WordPress/Dev.to publish
All free tools: DuckDuckGo, Groq LLM, WordPress XML-RPC or Dev.to API
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import json
import time
import requests
# from duckduckgo_search import DDGS
from ddgs import DDGS
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from core.logger import get_logger
from core.config import GROQ_API_KEY,DEVTO_API_KEY
from core.errors import PipelineError
import re
from markdownify import markdownify

logger = get_logger("blog_agent")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="openai/gpt-oss-20b",
    model_kwargs={"response_format": {"type": "json_object"}}
)

class BlogAgent:
    """
    Full SEO blog pipeline:
    1. Research keyword topic with DuckDuckGo
    2. Write structured SEO blog post with Groq
    3. Publish to WordPress or Dev.to
    """

    # ── Step 1: Research ──────────────────────────────────────
    def research_keyword(self, keyword: str) -> dict:
        """Search for information about the keyword topic."""
        logger.info(f"Researching keyword: '{keyword}'")

        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(keyword, max_results=6):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", "")[:400],
                        "url": r.get("href", "")
                    })
            logger.info(f"Found {len(results)} research sources")
        except Exception as e:
            logger.warning(f"Search failed: {e}")

        # Also search for related questions (people also ask)
        paa_results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(f"{keyword} how why what", max_results=3):
                    paa_results.append(r.get("body", "")[:200])
        except:
            pass

        return {
            "sources": results,
            "related_questions": paa_results,
            "keyword": keyword
        }

    # ── Step 2: Write SEO Blog Post ───────────────────────────
    def write_blog_post(self, keyword: str, research: dict) -> dict:
        """Write a structured, SEO-optimised blog post."""
        logger.info(f"Writing blog post for: '{keyword}'")

        sources_text = "\n\n".join([
            f"Source: {s['title']}\n{s['snippet']}"
            for s in research["sources"][:5]
        ])

        prompt = f"""You are an expert SEO content writer.

Target keyword: "{keyword}"

Research findings:
{sources_text}

Write a comprehensive, SEO-optimised blog post. Return ONLY valid JSON:
{{
  "title": "SEO-optimised H1 title containing the keyword (max 65 chars)",
  "meta_description": "Meta description for Google (150-160 chars, include keyword)",
  "slug": "url-friendly-slug-with-hyphens",
  "content": "Full blog post in HTML format. Include:\\n- Introduction (2-3 paragraphs)\\n- At least 4 H2 sections with relevant subheadings\\n- Each section: 2-3 paragraphs with specific facts from research\\n- Bullet lists where appropriate\\n- A conclusion with a clear call to action\\n- Use 
, 
, 
, 
, 
,  tags\\n- Minimum 800 words\\n- Include keyword naturally 4-6 times",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "focus_keyword": "{keyword}",
  "word_count_estimate": 900,
  "reading_time_minutes": 4
}}

Write genuinely useful content — not generic AI filler. Use the research facts.
No markdown code blocks. Return ONLY the JSON object."""

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            post_data = self.extract_json(raw)
            logger.info(f"Blog post written: '{post_data.get('title')}'")
            return post_data
        except Exception as e:
            logger.exception("Failed to parse LLM response")
            logger.error(raw)
            raise PipelineError(f"Blog writing failed for '{keyword}'") from e

    # ── Step 3a: Publish to WordPress ─────────────────────────
    def publish_to_wordpress(
        self,
        post_data: dict,
        wp_url: str,
        wp_username: str,
        wp_password: str,
        status: str = "draft"  # "draft" for review, "publish" for live
    ) -> dict:
        """Publish post to WordPress via XML-RPC."""
        try:
            from wordpress_xmlrpc import Client, WordPressPost
            from wordpress_xmlrpc.methods.posts import NewPost

            client = Client(
                f"{wp_url}/xmlrpc.php",
                wp_username,
                wp_password
            )

            post = WordPressPost()
            post.title = post_data["title"]
            post.content = post_data["content"]
            post.slug = post_data["slug"]
            post.terms_names = {"post_tag": post_data["tags"]}
            post.post_status = status
            post.excerpt = post_data["meta_description"]

            post_id = client.call(NewPost(post))
            post_url = f"{wp_url}/?p={post_id}"

            logger.info(f"Published to WordPress: ID {post_id}")
            return {
                "platform": "wordpress",
                "post_id": post_id,
                "url": post_url,
                "status": status,
                "title": post_data["title"]
            }
        except ImportError:
            raise PipelineError("wordpress_xmlrpc not installed: pip install python-wordpress-xmlrpc")
        except Exception as e:
            raise PipelineError(f"WordPress publish failed: {e}") from e

    # ── Step 3b: Publish to Dev.to (free alternative) ─────────
    def publish_to_devto(
        self,
        post_data: dict,
        api_key: str,
        published: bool = False  # False = draft, True = live
    ) -> dict:
        """Publish post to Dev.to — completely free, no WordPress needed."""
        logger.info("Publishing to Dev.to...")

        markdown_content = markdownify(post_data["content"])

        payload = {
            "article": {
                "title": post_data["title"],
                "body_markdown": markdown_content,
                "published": published,
                "tags": [t.lower().replace(" ", "")for t in post_data["tags"][:4]],  # Dev.to allows max 4 tags
                "description": post_data["meta_description"],
                "canonical_url": None
            }
        }

        res = requests.post(
            "https://dev.to/api/articles",
            headers={
                "api-key": api_key,
                "Content-Type": "application/json"
            },
            json=payload
        )
        print("Status:", res.status_code)
        print("Response:", res.text)

        res.raise_for_status()
        data = res.json()

        logger.info(f"Published to Dev.to: {data.get('url')}")
        return {
            "platform": "devto",
            "post_id": data.get("id"),
            "url": data.get("url"),
            "status": "published" if published else "draft",
            "title": post_data["title"]
        }

    def extract_json(self, text: str):
        text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
        text = text.replace("```", "")

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found.")

        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Handle unescaped literal line breaks/control chars from LLM
            return json.loads(json_str, strict=False)

    # ── Full Pipeline Runner ───────────────────────────────────
    def run(
        self,
        keyword: str,
        platform: str = "devto",  # "wordpress" or "devto"
        publish: bool = False,
        **platform_kwargs
    ) -> dict:
        """
        Full blog pipeline: keyword → research → write → publish.

        Args:
            keyword: Target SEO keyword
            platform: "wordpress" or "devto"
            publish: True = go live, False = save as draft
            **platform_kwargs: Platform-specific credentials
        """
        logger.info(f"Blog Agent starting: '{keyword}'  -> {platform}")

        # Research
        research = self.research_keyword(keyword)
        time.sleep(1)  # avoid rate limiting

        # Write
        post_data = self.write_blog_post(keyword, research)

        result = {
            "keyword": keyword,
            "title": post_data["title"],
            "meta_description": post_data["meta_description"],
            "word_count": post_data.get("word_count_estimate", 0),
            "tags": post_data["tags"],
            "sources_used": len(research["sources"]),
            "published": False,
            "platform": platform
        }

        # Publish
        if platform == "devto" and platform_kwargs.get("api_key"):
            pub_result = self.publish_to_devto(
                post_data,
                api_key=platform_kwargs["api_key"],
                published=publish
            )
            result.update(pub_result)
            result["published"] = publish

        elif platform == "wordpress":
            pub_result = self.publish_to_wordpress(
                post_data,
                wp_url=platform_kwargs.get("wp_url", ""),
                wp_username=platform_kwargs.get("wp_username", ""),
                wp_password=platform_kwargs.get("wp_password", ""),
                status="publish" if publish else "draft"
            )
            result.update(pub_result)
            result["published"] = publish
        else:
            # Preview only — print the post
            result["content_preview"] = post_data["content"][:500]
            logger.info("No platform credentials — preview mode only")

        logger.info(f"Blog Agent complete: '{post_data['title']}'")
        return result


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    agent = BlogAgent()

    # Test run — preview only (no publish credentials needed)
    result = agent.run(
        keyword="AI automation for small business India 2026",
        platform="devto",
        publish=True,
        api_key=DEVTO_API_KEY
    )

    # result = agent.run(
    #     keyword="How to use AI automation in your small business",
    #     platform="devto",
    #     publish=True,  # goes live on dev.to
    #     api_key=DEVTO_API_KEY
    # )
    print(f"\n{'='*50}")
    print(f"Title: {result['title']}")
    print(f"Meta: {result['meta_description']}")
    print(f"Word count: ~{result['word_count']}")
    print(f"Tags: {', '.join(result['tags'])}")
    print(f"Sources used: {result['sources_used']}")
    print(f"Status: {'Published' if result['published'] else 'Draft/Preview'}")
    if result.get("url"):
        print(f"URL: {result['url']}")