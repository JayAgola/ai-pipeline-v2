"""
Multi-Agent Pipeline
Research Agent → Script Agent
Uses LangGraph for orchestration, Groq for LLM, DuckDuckGo for research.
All free.
"""
import os
import json
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from duckduckgo_search import DDGS
from core.logger import get_logger
from core.errors import ScriptGenerationError
from core.config import GROQ_API_KEY

logger = get_logger("multi_agent")

# ── Shared State ──────────────────────────────────────────────
class PipelineState(TypedDict):
    """State shared between all agents in the pipeline."""
    topic: str                    # input: video topic
    research_query: str           # Research Agent sets this
    research_results: list        # Research Agent fills this
    research_summary: str         # Research Agent summarises
    script_data: dict             # Script Agent fills this
    error: str                    # any agent can set this
    messages: Annotated[list, operator.add]  # conversation log

# ── LLM Setup ─────────────────────────────────────────────────
llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.1-8b-instant"
)

# ── Research Agent ─────────────────────────────────────────────
def research_agent(state: PipelineState) -> PipelineState:
    """
    Research Agent: searches for facts and data about the topic.
    Uses DuckDuckGo (free, no API key) to find real information.
    """
    topic = state["topic"]
    logger.info(f"Research Agent: searching for '{topic}'")

    # Step 1: Ask LLM what to search for
    query_prompt = f"""You are a research assistant. 
For this video topic: "{topic}"
Generate the BEST search query to find relevant facts, statistics, and current information.
Return ONLY the search query, nothing else. Max 10 words."""

    query_response = llm.invoke([HumanMessage(content=query_prompt)])
    search_query = query_response.content.strip().strip('"')
    logger.info(f"Search query: '{search_query}'")

    # Step 2: Search DuckDuckGo (free)
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(search_query, max_results=5):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", "")[:300],
                    "url": r.get("href", "")
                })
        logger.info(f"Found {len(results)} search results")
    except Exception as e:
        logger.warning(f"Search failed: {e}. Continuing without web data.")
        results = []

    # Step 3: Summarise findings
    if results:
        results_text = "\n\n".join([
            f"Source: {r['title']}\n{r['snippet']}"
            for r in results
        ])
        summary_prompt = f"""Summarise these search results about "{topic}" into 5 key facts:

{results_text}

Format as a numbered list of specific, credible facts with any statistics mentioned.
Keep each fact to 1-2 sentences. Be specific, not generic."""

        summary_response = llm.invoke([HumanMessage(content=summary_prompt)])
        research_summary = summary_response.content
    else:
        research_summary = f"No web results found. Topic: {topic}. Use general knowledge."

    logger.info("Research Agent complete")
    return {
        **state,
        "research_query": search_query,
        "research_results": results,
        "research_summary": research_summary,
        "messages": state.get("messages", []) + [
            {"role": "research_agent", "content": f"Research complete: {len(results)} sources found"}
        ]
    }

# ── Script Agent ───────────────────────────────────────────────
def script_agent(state: PipelineState) -> PipelineState:
    """
    Script Agent: uses research to write a grounded video script.
    Produces factual, credible content — not generic AI fluff.
    """
    topic = state["topic"]
    research = state.get("research_summary", "No research available.")

    logger.info(f"Script Agent: writing script for '{topic}'")

    prompt = f"""You are a professional video script writer.

Topic: {topic}

Research findings:
{research}

Using the research above, write a 30-second educational video script.
The script must reference specific facts or data from the research — not generic claims.

Return ONLY valid JSON with these exact fields:
{{
  "title": "video title (max 60 chars, include a specific number or stat if available)",
  "subtitle": "subtitle that references the research (max 80 chars)",
  "script": "full narration (60-90 words, cite 1-2 specific facts from research)",
  "points": [
    "bullet point 1 with specific fact/stat",
    "bullet point 2 with specific fact/stat", 
    "bullet point 3 with specific fact/stat"
  ],
  "channel_name": "AI Business Insights",
  "sources_used": {len(state.get('research_results', []))}
}}

No markdown, no backticks. Only valid JSON."""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        script_data = json.loads(raw)
        logger.info(f"Script Agent complete: '{script_data.get('title', 'untitled')}'")

        return {
            **state,
            "script_data": script_data,
            "messages": state.get("messages", []) + [
                {"role": "script_agent", "content": f"Script written: {script_data.get('title')}"}
            ]
        }
    except json.JSONDecodeError as e:
        logger.error(f"Script Agent JSON error: {e}")
        return {
            **state,
            "error": f"Script generation failed: {e}",
            "script_data": {}
        }

# ── Quality Check Node ─────────────────────────────────────────
def quality_check(state: PipelineState) -> str:
    """
    Router: checks if the script is good quality.
    Returns "done" if good, "retry" if needs improvement.
    LangGraph uses this to decide which node runs next.
    """
    script = state.get("script_data", {})
    error = state.get("error", "")

    if error:
        logger.warning(f"Quality check: error detected — {error}")
        return "done"  # don't retry on error, just finish

    script_text = script.get("script", "")
    if len(script_text) < 50:
        logger.warning("Quality check: script too short")
        return "retry"  # too short — retry script agent

    logger.info("Quality check: script passed ✓")
    return "done"

# ── Build the Graph ────────────────────────────────────────────
def build_graph() -> StateGraph:
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("research", research_agent)
    graph.add_node("script", script_agent)

    # Set entry point
    graph.set_entry_point("research")

    # research → script (always)
    graph.add_edge("research", "script")

    # script → quality check → done or retry
    graph.add_conditional_edges(
        "script",
        quality_check,
        {
            "done": END,
            "retry": "script"  # retry the script node if quality fails
        }
    )

    return graph.compile()

# ── Main Runner ────────────────────────────────────────────────
def run_multi_agent_pipeline(topic: str) -> dict:
    """Run the full Research → Script pipeline."""
    logger.info(f"Starting multi-agent pipeline for: '{topic}'")

    app = build_graph()
    initial_state: PipelineState = {
        "topic": topic,
        "research_query": "",
        "research_results": [],
        "research_summary": "",
        "script_data": {},
        "error": "",
        "messages": []
    }

    result = app.invoke(initial_state)

    logger.info(f"Pipeline complete. Messages: {len(result.get('messages', []))}")
    return result


if __name__ == "__main__":
    topic = input("Enter a topic: ") or "How AI is reducing costs for Indian small businesses"

    print(f"\n🔬 Running multi-agent pipeline for: '{topic}'\n")
    result = run_multi_agent_pipeline(topic)

    print("\n" + "="*50)
    if result.get("script_data"):
        sd = result["script_data"]
        print(f"TITLE: {sd.get('title')}")
        print(f"SUBTITLE: {sd.get('subtitle')}")
        print(f"\nSCRIPT:\n{sd.get('script')}")
        print(f"\nSLIDE POINTS:")
        for p in sd.get("points", []):
            print(f"  → {p}")
        print(f"\nSources used: {sd.get('sources_used', 0)}")
        print(f"Research query: {result.get('research_query')}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    # Print the full agent conversation for debugging
    print("\n--- Agent Messages ---")

    for msg in result.get("messages", []):
        print(f"[{msg['role']}]: {msg['content']}")
