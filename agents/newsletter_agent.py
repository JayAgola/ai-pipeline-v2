"""
Newsletter Agent
Fetches trending topics from RSS feeds, summarises with AI,
writes a newsletter, and sends via Mailchimp.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import feedparser
import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError
from langchain_groq import ChatGroq
from datetime import datetime
from core.logger import get_logger
from core.errors import PipelineError

logger = get_logger("newsletter_agent")

# Free RSS feeds — no signup needed
RSS_FEEDS = {
    "AI & Tech": [
        "https://feeds.feedburner.com/TechCrunch",
        "https://hnrss.org/frontpage",
        "https://www.artificialintelligence-news.com/feed/",
    ],
    "Business": [
        "https://feeds.feedburner.com/entrepreneur/latest",
        "https://www.inc.com/rss",
    ],
    "India Business": [
        "https://economictimes.indiatimes.com/tech/rss.cms",
        "https://feeds.feedburner.com/moneycontrol-latestnews",
    ]
}

class NewsletterAgent:
    """
    Fully automated newsletter pipeline:
    RSS feeds → AI curation → newsletter draft → Mailchimp send
    """

    def __init__(self, niche: str = "AI & Tech"):
        self.niche = niche
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model="openai/gpt-oss-20b"
        )
        self.mailchimp = MailchimpMarketing.Client()
        self.mailchimp.set_config({
            "api_key": os.getenv("MAILCHIMP_API_KEY"),
            "server": os.getenv("MAILCHIMP_SERVER")
        })
        self.audience_id = os.getenv("MAILCHIMP_AUDIENCE_ID")
        logger.info(f"NewsletterAgent ready for niche: {niche}")

    def fetch_trending_articles(self, max_per_feed: int = 3) -> list:
        """Fetch latest articles from RSS feeds for the chosen niche."""
        feeds = RSS_FEEDS.get(self.niche, RSS_FEEDS["AI & Tech"])
        articles = []

        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:max_per_feed]:
                    articles.append({
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", "")[:300],
                        "link": entry.get("link", ""),
                        "published": entry.get("published", "")
                    })
                logger.info(f"Fetched {min(max_per_feed, len(feed.entries))} articles from {feed_url[:40]}")
            except Exception as e:
                logger.warning(f"Feed failed: {feed_url[:40]} — {e}")

        logger.info(f"Total articles fetched: {len(articles)}")
        return articles[:10]  # cap at 10 articles

    def curate_and_summarise(self, articles: list) -> str:
        """Use Groq LLM to curate and summarise articles into newsletter content."""
        article_text = ""
        for i, a in enumerate(articles, 1):
            article_text += f"{i}. {a['title']}\n{a['summary'][:200]}\n\n"

        prompt = f"""You are a professional newsletter writer for a {self.niche} audience.

Based on these recent articles:
{article_text}

Write a professional, engaging weekly newsletter with:
1. A compelling subject line (prefix with SUBJECT:)
2. A brief intro paragraph (2-3 sentences, friendly tone)
3. Top 5 stories — each with: bold title, 2-sentence summary, why it matters
4. A brief closing paragraph with a call to action
5. Sign off as "The AI Insights Team"

Format as clean HTML suitable for email.
Use 
 for section headers, 
 for paragraphs,  for story titles.
Keep total length under 600 words.
Start your response with SUBJECT: on the first line."""

        response = self.llm.invoke(prompt)
        return response.content

    def parse_subject_and_body(self, content: str) -> tuple:
        """Extract subject line and HTML body from LLM output."""
        lines = content.strip().split("\n")
        subject = "Your Weekly AI Newsletter"
        body_lines = []

        for i, line in enumerate(lines):
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            else:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()

        # Wrap in basic HTML if not already wrapped
        if not body.startswith("<"):
            body = f"{body}"

        return subject, body

    def send_campaign(self, subject: str, html_body: str) -> dict:
        """Create and send a Mailchimp campaign."""
        try:
            # Step 1: Create campaign
            campaign = self.mailchimp.campaigns.create({
                "type": "regular",
                "recipients": {
                    "list_id": self.audience_id
                },
                "settings": {
                    "subject_line": subject,
                    "from_name": "AI Business Insights",
                    "reply_to": os.getenv("EMAIL_FROM", "hello@example.com"),
                    "title": f"Newsletter {datetime.now().strftime('%Y-%m-%d')}"
                }
            })
            campaign_id = campaign["id"]
            logger.info(f"Campaign created: {campaign_id}")

            # Step 2: Set campaign content
            self.mailchimp.campaigns.set_content(campaign_id, {
                "html": html_body
            })
            logger.info("Content set")

            # Step 3: Send campaign
            self.mailchimp.campaigns.send(campaign_id)
            logger.info(f"Campaign sent: {campaign_id}")

            return {
                "campaign_id": campaign_id,
                "subject": subject,
                "status": "sent",
                "sent_at": datetime.now().isoformat()
            }

        except ApiClientError as e:
            logger.error(f"Mailchimp API error: {e.text}")
            raise PipelineError(f"Mailchimp send failed: {e.text}") from e

    def run(self, send: bool = False) -> dict:
        """
        Full newsletter pipeline.
        Set send=False to preview without sending (safe for testing).
        """
        logger.info(f"Starting newsletter pipeline for: {self.niche}")

        # Fetch articles
        articles = self.fetch_trending_articles()
        if not articles:
            raise PipelineError("No articles fetched — check RSS feeds")

        # Generate newsletter
        content = self.curate_and_summarise(articles)
        subject, html_body = self.parse_subject_and_body(content)

        logger.info(f"Newsletter generated. Subject: '{subject}'")
        logger.info(f"Word count: ~{len(html_body.split())} words")

        result = {
            "niche": self.niche,
            "articles_used": len(articles),
            "subject": subject,
            "html_preview": html_body[:500] + "...",
            "sent": False
        }

        if send:
            send_result = self.send_campaign(subject, html_body)
            result.update(send_result)
            result["sent"] = True
        else:
            logger.info("Preview mode — not sent. Set send=True to send.")
            print(f"\n{'='*50}")
            print(f"SUBJECT: {subject}")
            print(f"{'='*50}")
            print(html_body[:800])
            print("...")

        return result


if __name__ == "__main__":
    agent = NewsletterAgent(niche="AI & Tech")

    # First run in preview mode (send=False)
    result = agent.run(send=False)

    print(f"\n✅ Newsletter generated!")
    print(f"Subject: {result['subject']}")
    print(f"Articles used: {result['articles_used']}")
    print("\nSet send=True to actually send via Mailchimp.")