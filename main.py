import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable, List

from extractors.arxiv import ArxivAPIExtractor
from extractors.base import BaseExtractor, Document
from extractors.commoncrawl import CommonCrawlExtractor
from extractors.github_code import GitHubAPIExtractor
from extractors.gutenberg import GutenbergExtractor
from extractors.huggingface_ds import HuggingFaceStreamingExtractor
from extractors.pubmed import PubMedBulkExtractor, PubMedEntrezExtractor
from extractors.stackexchange import StackExchangeExtractor
from extractors.wikimedia import WikimediaDumpExtractor
from processors.chunking import chunk_text_tiktoken
from processors.cleaning import clean_text, is_valid_text
from processors.dedup import ExactDeduplicator, SemanticDeduplicator
from utils.checkpoint import CheckpointStore
from utils.io_utils import JsonlGzWriter, ParquetBatchWriter
from utils.logging_utils import setup_logging


def build_extractor(args: argparse.Namespace) -> BaseExtractor:
    if args.source == "arxiv_api":
        return ArxivAPIExtractor(search_query=args.query, start=args.start, max_results=args.max_results)
    if args.source == "commoncrawl":
        return CommonCrawlExtractor(warc_path=args.input_path, s3_key=args.s3_key)
    if args.source == "wikimedia":
        return WikimediaDumpExtractor(args.input_path)
    if args.source == "gutenberg":
        return GutenbergExtractor(args.input_path)
    if args.source == "huggingface":
        return HuggingFaceStreamingExtractor(args.dataset, split=args.split, text_field=args.text_field)
    if args.source == "stackexchange":
        return StackExchangeExtractor(posts_xml=args.posts_xml, comments_xml=args.comments_xml)
    if args.source == "pubmed_api":
        return PubMedEntrezExtractor(pmc_ids=args.pmc_ids)
    if args.source == "pubmed_bulk":
        return PubMedBulkExtractor(xml_dir=args.input_path)
    if args.source == "github":
        return GitHubAPIExtractor(token=args.github_token, repos=args.repos)
    raise ValueError(f"Unsupported source: {args.source}")


def process_doc(
    doc: Document,
    deduper,
    enable_chunking: bool,
    chunk_size: int,
) -> List[dict]:
    text = clean_text(doc.text)
    if not is_valid_text(text):
        return []
    if deduper.is_duplicate(text):
        return []

    texts = list(chunk_text_tiktoken(text, chunk_size=chunk_size)) if enable_chunking else [text]
    return [{"text": t, "meta": doc.meta} for t in texts if t.strip()]


def run_pipeline(args: argparse.Namespace) -> None:
    logger = setup_logging(level=logging.INFO)
    checkpoint = CheckpointStore(args.checkpoint)
    extractor = build_extractor(args)

    if args.output_format == "jsonl":
        writer = JsonlGzWriter(args.output_path, flush_every=args.write_batch_size)
    else:
        writer = ParquetBatchWriter(args.output_path, row_group_size=args.write_batch_size)

    deduper = SemanticDeduplicator() if args.semantic_dedup else ExactDeduplicator()

    start_idx = checkpoint.get("processed_docs", 0)
    processed_docs = 0
    written_records = checkpoint.get("written_records", 0)

    logger.info("Start pipeline | source=%s | resume_from=%s", args.source, start_idx)

    with ThreadPoolExecutor(max_workers=args.num_workers) as pool:
        futures = []
        for i, doc in enumerate(extractor.stream()):
            if i < start_idx:
                continue
            futures.append(pool.submit(process_doc, doc, deduper, args.enable_chunking, args.chunk_size))
            if len(futures) >= args.num_workers * 8:
                for fut in futures:
                    for record in fut.result():
                        writer.write(record)
                        written_records += 1
                futures.clear()
                processed_docs = i + 1
                checkpoint.save({"processed_docs": processed_docs, "written_records": written_records})
                logger.info("Progress | docs=%s | records=%s", processed_docs, written_records)

        for fut in futures:
            for record in fut.result():
                writer.write(record)
                written_records += 1

    writer.close()
    checkpoint.save({"processed_docs": processed_docs, "written_records": written_records})
    logger.info("Pipeline completed | docs=%s | records=%s", processed_docs, written_records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Modular ETL pipeline for LLM pretraining corpora")
    parser.add_argument("--source", required=True)
    parser.add_argument("--input-path")
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--output-format", choices=["jsonl", "parquet"], default="jsonl")
    parser.add_argument("--write-batch-size", type=int, default=1000)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--checkpoint", default="checkpoints/state.json")

    parser.add_argument("--enable-chunking", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=2048)
    parser.add_argument("--semantic-dedup", action="store_true")

    parser.add_argument("--query", default="cat:cs.CL")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--max-results", type=int, default=100)
    parser.add_argument("--s3-key")

    parser.add_argument("--dataset")
    parser.add_argument("--split", default="train")
    parser.add_argument("--text-field", default="text")

    parser.add_argument("--posts-xml")
    parser.add_argument("--comments-xml")

    parser.add_argument("--pmc-ids", nargs="*", default=[])

    parser.add_argument("--github-token")
    parser.add_argument("--repos", nargs="*", default=[])

    return parser.parse_args()


if __name__ == "__main__":
    run_pipeline(parse_args())
