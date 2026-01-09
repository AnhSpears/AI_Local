from core.llm import generate
from core.memory import ConversationMemory
from core.long_memory import LongTermMemory
from rich.console import Console
from core.knowledge_base import KnowledgeBase
from core.document_rag import DocumentRAG

doc_rag = DocumentRAG() 
knowledge = KnowledgeBase()
console = Console()
memory = ConversationMemory()
long_memory = LongTermMemory()

def detect_learning_intent(text: str):
    keywords = [
        "tôi đang học",
        "tôi học",
        "tôi muốn học",
        "đang nghiên cứu",
        "đang tìm hiểu"
    ]
    text_lower = text.lower()
    for k in keywords:
        if k in text_lower:
            return text_lower.replace(k, "").strip()
    return None

def main():
    console.print("[bold green]AI CLI đã sẵn sàng[/bold green]")
    doc_rag.load_documents()
    while True:
        prompt = console.input("[bold blue]> [/bold blue]")
        if prompt.lower() in ("exit", "quit"):
            break

        memory.add("Người dùng", prompt)

        # 1️⃣ Phát hiện intent học tập → LƯU NGAY
        learning_subject = detect_learning_intent(prompt)
        if learning_subject:
            long_memory.add_learning(
                subject=learning_subject,
                detail=prompt
    )

            file_path = knowledge.save_learning(
                subject=learning_subject,
                detail=prompt
    )

            console.print(f"[dim]📂 Đã lưu tri thức tại: {file_path}[/dim]")

        # 2️⃣ Lấy trí nhớ dài hạn (ưu tiên)
        long_term_context = "\n".join(long_memory.search_learning())

        # 3️⃣ Gọi LLM
        doc_context = "\n".join(doc_rag.search(prompt))

        response = generate(
            prompt,
            memory.format()
            + "\n"
            + long_term_context
            + "\n"
            + doc_context
        )

        memory.add("AI", response)
        console.print(response)

if __name__ == "__main__":
    main()
