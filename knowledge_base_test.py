from agents.knowledge_base import ContentKnowledgeBase
from agents.script_agent import ScriptAgent

kb = ContentKnowledgeBase()
agent = ScriptAgent()

# Seed 3 scripts
test_topics = [
    "How AI is helping small businesses save money",
    "Top 5 AI tools every small business owner needs",
    "Why small businesses should adopt AI automation now"
]

print("Seeding knowledge base...")
for topic in test_topics:
    script = agent.generate(topic)
    kb.store_script(topic, script)
    print(f"Stored: '{script['title']}'")

print(f"\nKB now has {kb.count_total()} scripts")

# Now test a related topic
print("\nGenerating script for related topic WITH KB awareness...")
new_script = agent.generate(
    "How small businesses can automate operations with AI"
)
print(f"\nTitle: {new_script['title']}")
print(f"Fresh angle: {new_script.get('is_fresh_angle', 'unknown')}")
print(f"\nScript:\n{new_script['script']}")