# Modular LLM Pretraining ETL Pipeline

Pipeline Python dạng module để ingest, extract, clean, dedup, chunk và ghi dữ liệu pretraining ở định dạng `jsonl.gz` hoặc `parquet`.

## Cấu trúc thư mục

- `extractors/`: module ingest theo từng nguồn (Common Crawl, arXiv, Wikimedia, Gutenberg, Hugging Face, StackExchange, PubMed, GitHub).
- `processors/`: làm sạch, dedup (exact + MinHash/LSH), chunking token.
- `utils/`: logging, checkpoint, batch writers.
- `main.py`: CLI orchestration + multi-thread processing.

## Output schema

```json
{"text": "Nội dung văn bản làm sạch...", "meta": {"source": "arxiv", "url": "...", "timestamp": "..."}}
```

## Ví dụ chạy

```bash
python main.py \
  --source wikimedia \
  --input-path viwiki-latest-pages-articles.xml.bz2 \
  --output-path data/wiki.jsonl.gz \
  --output-format jsonl \
  --enable-chunking \
  --chunk-size 2048 \
  --semantic-dedup
```

## Gợi ý scale-out

- **Ray**: đổi `ThreadPoolExecutor` thành `ray.remote` tasks cho cluster nhiều node.
- **PySpark**: wrap extractor output thành Spark DataFrame rồi dùng UDF cleaning/chunking.
- **Checkpointing**: file JSON local hoặc backend Redis/S3 cho distributed workers.

## Nguồn dữ liệu lớn

- Common Crawl: đọc `.warc/.warc.gz` qua `warcio`, hoặc lấy object trực tiếp từ S3 bucket `commoncrawl`.
- arXiv: API (`export.arxiv.org`) hoặc ingest tar/bulk mirror từ `s3://arxiv`.
- Gutenberg: dùng `rsync` mirror trước khi xử lý text.
- StackExchange: parse `Posts.xml`, `Comments.xml` và join theo `PostId` / `ParentId`.
- GitHub: ưu tiên query repo bằng BigQuery public dataset rồi crawl file code qua GitHub API với repo license mở.
