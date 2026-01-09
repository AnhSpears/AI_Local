from core.memory import ConversationMemory


def test_memory_format():
    m = ConversationMemory(max_turns=2)
    m.add("user", "xin chào")
    m.add("assistant", "chào bạn")
    fmt = m.format()
    assert "user: xin chào" in fmt
    assert "assistant: chào bạn" in fmt
