import os
import uuid
import chromadb
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from pypdf.errors import PdfStreamError

class DocumentRAG:
    def __init__(self, path="documents", db_path="data/document_rag"):
        self.path = path
        os.makedirs(self.path, exist_ok=True)

        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="document_rag"
        )

        self.embedder = SentenceTransformer("BAAI/bge-base-en-v1.5")

    def load_documents(self):
        for root, _, files in os.walk(self.path):
            for file in files:
                full_path = os.path.join(root, file)

                try:
                    if file.lower().endswith(".pdf"):
                        self._load_pdf(full_path)
                    elif file.lower().endswith((".txt", ".md", ".py", ".js", ".java", ".cpp")):
                        self._load_text(full_path)
                except Exception as e:
                    print(f"[WARN] Bỏ qua file lỗi: {full_path}")
                    print(f"       Lý do: {e}")

    def _load_pdf(self, path):
        try:
            reader = PdfReader(path)
        except PdfStreamError:
            raise RuntimeError("File không phải PDF hợp lệ")

        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        if text.strip():
            self._add_chunks(text, source=path)

    def _load_text(self, path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        if text.strip():
            self._add_chunks(text, source=path)

    def _add_chunks(self, text, source, chunk_size=500):
        words = text.split()
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])

            embedding = self.embedder.encode(chunk).tolist()

            self.collection.add(
                ids=[str(uuid.uuid4())],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": source}]
            )

    def search(self, query, n_results=5):
        embedding = self.embedder.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results
        )
        return results["documents"][0] if results["documents"] else []
