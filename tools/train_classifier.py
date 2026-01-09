"""Train a simple classifier using existing documents as weak labels.

Usage:
  python tools/train_classifier.py --source documents --limit 200

- Builds a dataset by scanning `--source` and using KnowledgeBase.detect_topic as weak labels.
- Trains embedding-based LogisticRegression and saves model to `models/classifier.pkl`.
"""
import argparse
import logging
from pathlib import Path
from core.classifier import SimpleClassifier
from core.knowledge_base import KnowledgeBase
from tools.ingest_and_classify import extract_text

logging.basicConfig(level=logging.INFO)


def collect_dataset(src: Path, limit: int = 1000):
    kb = KnowledgeBase()
    texts = []
    labels = []

    for root, _, files in src.rglob("*"):
        pass

    # simpler: iterate files under src
    cnt = 0
    for f in src.rglob("*"):
        if f.is_file():
            try:
                txt = extract_text(f)
                sample = (f.name + " \n" + txt[:4000]).strip()
                label = kb.detect_topic(sample)
                texts.append(sample)
                labels.append(label)
                cnt += 1
                if cnt >= limit:
                    break
            except Exception as e:
                logging.warning(f"Skip {f}: {e}")

    logging.info(f"Collected {len(texts)} samples")
    return texts, labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="documents", help="Documents source folder")
    parser.add_argument("--limit", type=int, default=500, help="Max samples")
    args = parser.parse_args()

    src = Path(args.source)
    texts, labels = collect_dataset(src, limit=args.limit)

    clf = SimpleClassifier()
    clf.train(texts, labels)
    logging.info("Classifier trained and saved.")


if __name__ == "__main__":
    main()
