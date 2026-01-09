import chromadb
from sentence_transformers import SentenceTransformer
import uuid
import datetime
import os

class LongTermMemory:
    def __init__(self, path="data/memory"):
        os.makedirs(path, exist_ok=True)

        # ✅ Persistent client (CHUẨN cho ChromaDB mới)
        self.client = chromadb.PersistentClient(path=path)

        self.collection = self.client.get_or_create_collection(
            name="ai_memory"
        )

        self.embedder = SentenceTransformer("BAAI/bge-base-en-v1.5")

    def add_learning(self, subject: str, detail: str):
        text = f"Người dùng đang học về {subject}. Nội dung: {detail}"
        embedding = self.embedder.encode(text).tolist()

        self.collection.add(
            ids=[str(uuid.uuid4())],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "type": "learning",
                "subject": subject,
                "time": datetime.datetime.now().isoformat()
            }]
        )
        # ❌ KHÔNG cần persist() – ChromaDB mới tự lưu

    def search_learning(self):
        query = "Người dùng đang học những gì"
        embedding = self.embedder.encode(query).tolist()

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=5
        )


        return results["documents"][0] if results["documents"] else []
