from agents.knowledge_base import ContentKnowledgeBase

kb = ContentKnowledgeBase()

# Test topic that should find similar content
test_topic = "AI tools for small business owners"
similar = kb.search_similar(test_topic, threshold=0.5)

print(f"Similar past content for: '{test_topic}'")
print(f"Found {len(similar)} matches:\n")

for r in similar:
    print(f"  [{r['similarity']:.2f}] {r['title']}")