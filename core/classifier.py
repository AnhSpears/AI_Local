import os
import json
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import joblib

MODEL_ENV = "EMBEDDING_MODEL"
DEFAULT_EMBEDDING = os.getenv(MODEL_ENV, "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

MODEL_DIR = os.getenv("CLASSIFIER_MODEL_DIR", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "classifier.pkl")


class SimpleClassifier:
    def __init__(self, embedder_name: Optional[str] = None):
        self.embedder_name = embedder_name or DEFAULT_EMBEDDING
        self.embedder = SentenceTransformer(self.embedder_name)
        self.model = None  # sklearn pipeline

    def _embed_texts(self, texts: List[str]):
        return self.embedder.encode(texts)

    def train(self, texts: List[str], labels: List[str], save: bool = True):
        X = self._embed_texts(texts)
        # pipeline: scaler + logistic
        clf = LogisticRegression(max_iter=1000)
        pipeline = make_pipeline(StandardScaler(), clf)
        pipeline.fit(X, labels)
        self.model = pipeline
        if save:
            os.makedirs(MODEL_DIR, exist_ok=True)
            joblib.dump({"model": self.model, "embedder": self.embedder_name}, MODEL_PATH)
        return self

    def predict(self, text: str) -> Tuple[str, float]:
        if not self.model:
            self.load()
        emb = self._embed_texts([text])
        probs = self.model.predict_proba(emb)[0]
        classes = self.model.named_steps["logisticregression"].classes_
        # pick top
        import numpy as np

        idx = int(np.argmax(probs))
        return classes[idx], float(probs[idx])

    def load(self, path: Optional[str] = None):
        path = path or MODEL_PATH
        if not os.path.exists(path):
            raise FileNotFoundError("Classifier model not found. Train and save a model first.")
        data = joblib.load(path)
        self.model = data["model"] if isinstance(data, dict) else data
        self.embedder_name = data.get("embedder", self.embedder_name) if isinstance(data, dict) else self.embedder_name
        # ensure embedder matches
        if not hasattr(self, "embedder") or self.embedder.model_name != self.embedder_name:
            self.embedder = SentenceTransformer(self.embedder_name)
        return self

    def save(self, path: Optional[str] = None):
        path = path or MODEL_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({"model": self.model, "embedder": self.embedder_name}, path)
        return path
