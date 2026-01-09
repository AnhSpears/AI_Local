import os
import datetime

class KnowledgeBase:
    def __init__(self, base_path="knowledge"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def normalize(self, text: str) -> str:
        return (
            text.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )

    def detect_topic(self, subject: str) -> str:
        subject = subject.lower()

        if any(k in subject for k in ["ai", "agent", "rag", "machine learning"]):
            return "ai"
        if any(k in subject for k in ["python", "code", "program", "lập trình"]):
            return "programming"
        if any(k in subject for k in ["video", "content", "youtube", "tiktok"]):
            return "content_creation"
        if any(k in subject for k in ["cuộc sống", "cá nhân", "bản thân"]):
            return "personal"

        return "other"

    def save_learning(self, subject: str, detail: str):
        topic = self.detect_topic(subject)
        topic_path = os.path.join(self.base_path, topic)
        os.makedirs(topic_path, exist_ok=True)

        filename = self.normalize(subject) + ".md"
        file_path = os.path.join(topic_path, filename)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        content = f"""
## {subject}
**Thời gian:** {timestamp}

{detail}

---
"""

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(content)

        return file_path
