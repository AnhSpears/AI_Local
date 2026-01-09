import os
import shutil
import argparse
import logging
from pathlib import Path

from core.knowledge_base import KnowledgeBase
from core.document_rag import DocumentRAG
from core.classifier import SimpleClassifier
from pypdf import PdfReader

logging.basicConfig(level=logging.INFO)


def extract_text(path: Path) -> str:
    try:
        if path.suffix.lower() == ".pdf":
            reader = PdfReader(str(path))
            text = []
            for p in reader.pages:
                t = p.extract_text()
                if t:
                    text.append(t)
            return "\n".join(text)
        else:
            return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logging.warning(f"Không thể đọc {path}: {e}")
        return ""


def classify_and_copy(source: Path, dest: Path, dry_run: bool = False, auto_move: bool = True):
    kb = KnowledgeBase()
    clf = SimpleClassifier()
    try:
        clf.load()
    except Exception:
        logging.warning("Classifier model not found; falling back to KnowledgeBase heuristics.")
        clf = None

    # thresholds (configurable later)
    high = 0.80
    mid = 0.50

    doc_count = 0
    moved = 0

    for root, _, files in os.walk(source):
        for f in files:
            src = Path(root) / f
            # skip already in dest
            if dest in src.parents:
                continue

            doc_count += 1
            sample = (f + " \n" + extract_text(src)[:2000]).strip()

            if clf:
                topic, conf = clf.predict(sample)
            else:
                topic = kb.detect_topic(sample)
                conf = 1.0

            if auto_move:
                if conf >= high:
                    target_dir = dest / topic
                elif conf >= mid:
                    target_dir = Path("documents/suggested") / topic
                else:
                    target_dir = Path("documents/unclassified")
            else:
                target_dir = dest / topic

            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f

            if target.exists():
                logging.info(f"Bỏ qua (tồn tại): {target}")
                continue

            logging.info(f"[{topic} | {conf:.2f}] {src} -> {target}")
            if not dry_run:
                try:
                    shutil.copy2(src, target)
                    moved += 1
                except Exception as e:
                    logging.warning(f"Không copy được {src}: {e}")

    return doc_count, moved


def main():
    parser = argparse.ArgumentParser(description="Nhập liệu và phân loại tài liệu vào thư mục theo chủ đề")
    parser.add_argument("--source", default="documents", help="Thư mục nguồn (mặc định: documents)")
    parser.add_argument("--dest", default="documents/sorted", help="Thư mục đích (mặc định: documents/sorted)")
    parser.add_argument("--index", action="store_true", help="Sau khi phân loại, chạy indexing RAG")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ hiển thị hành động mà không copy")

    args = parser.parse_args()

    src = Path(args.source)
    dst = Path(args.dest)

    if not src.exists():
        logging.error(f"Thư mục nguồn không tồn tại: {src}")
        return

    logging.info(f"Quét: {src} -> {dst} (dry={args.dry_run})")
    total, moved = classify_and_copy(src, dst, dry_run=args.dry_run)
    logging.info(f"Tổng tệp: {total}, đã copy: {moved}")

    if args.index and not args.dry_run:
        logging.info("Bắt đầu indexing documents/sorted vào Chroma (DocumentRAG)")
        dr = DocumentRAG(path=str(dst), db_path="data/document_rag")
        dr.load_documents()
        logging.info("Indexing hoàn tất.")


if __name__ == "__main__":
    main()
