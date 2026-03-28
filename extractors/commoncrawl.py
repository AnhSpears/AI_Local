import gzip
import io
from typing import Iterable, Iterator, Optional

import boto3
from warcio.archiveiterator import ArchiveIterator

from .base import BaseExtractor, Document


class CommonCrawlExtractor(BaseExtractor):
    source_name = "commoncrawl"

    def __init__(self, warc_path: Optional[str] = None, s3_key: Optional[str] = None, bucket: str = "commoncrawl") -> None:
        self.warc_path = warc_path
        self.s3_key = s3_key
        self.bucket = bucket

    def _warc_stream(self) -> io.BufferedReader:
        if self.warc_path:
            if self.warc_path.endswith(".gz"):
                return gzip.open(self.warc_path, "rb")
            return open(self.warc_path, "rb")

        if not self.s3_key:
            raise ValueError("Provide either warc_path or s3_key")

        s3 = boto3.client("s3")
        obj = s3.get_object(Bucket=self.bucket, Key=self.s3_key)
        body = obj["Body"]
        if self.s3_key.endswith(".gz"):
            return gzip.GzipFile(fileobj=body)
        return body

    def stream(self) -> Iterable[Document]:
        with self._warc_stream() as fh:
            for record in ArchiveIterator(fh):
                if record.rec_type != "response":
                    continue
                try:
                    payload = record.content_stream().read().decode("utf-8", errors="ignore")
                except Exception:
                    continue
                url = record.rec_headers.get_header("WARC-Target-URI")
                timestamp = record.rec_headers.get_header("WARC-Date")
                yield Document(text=payload, meta={"source": self.source_name, "url": url, "timestamp": timestamp})


def iter_cc_paths(index_gz_file: str) -> Iterator[str]:
    """Read a Common Crawl paths file (wet.paths.gz / warc.paths.gz) in streaming mode."""
    with gzip.open(index_gz_file, "rt", encoding="utf-8") as fh:
        for line in fh:
            yield line.strip()
