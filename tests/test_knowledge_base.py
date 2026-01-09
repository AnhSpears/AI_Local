from core.knowledge_base import KnowledgeBase


def test_detect_topic_ai():
    kb = KnowledgeBase(base_path="knowledge_test")
    assert kb.detect_topic("Giới thiệu về AI và agent") == "ai"


def test_detect_topic_programming():
    kb = KnowledgeBase(base_path="knowledge_test")
    assert kb.detect_topic("Học lập trình Python cơ bản") == "programming"
