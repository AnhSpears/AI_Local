import gzip
import json
from pathlib import Path
from typing import Dict, Iterable, List

import pyarrow as pa
import pyarrow.parquet as pq


class JsonlGzWriter:
    def __init__(self, output_path: str, flush_every: int = 1000) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.flush_every = flush_every
        self._buffer: List[Dict] = []
        self._fh = gzip.open(self.output_path, "at", encoding="utf-8")

    def write(self, record: Dict) -> None:
        self._buffer.append(record)
        if len(self._buffer) >= self.flush_every:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        for item in self._buffer:
            self._fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        self._buffer.clear()

    def close(self) -> None:
        self.flush()
        self._fh.close()


class ParquetBatchWriter:
    def __init__(self, output_path: str, row_group_size: int = 50_000) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.row_group_size = row_group_size
        self._rows: List[Dict] = []
        self._writer = None

    def write(self, record: Dict) -> None:
        self._rows.append(record)
        if len(self._rows) >= self.row_group_size:
            self.flush()

    def flush(self) -> None:
        if not self._rows:
            return
        table = pa.Table.from_pylist(self._rows)
        if self._writer is None:
            self._writer = pq.ParquetWriter(str(self.output_path), table.schema, compression="zstd")
        self._writer.write_table(table)
        self._rows.clear()

    def close(self) -> None:
        self.flush()
        if self._writer is not None:
            self._writer.close()


def batched(iterable: Iterable[Dict], batch_size: int) -> Iterable[List[Dict]]:
    buffer: List[Dict] = []
    for row in iterable:
        buffer.append(row)
        if len(buffer) >= batch_size:
            yield buffer
            buffer = []
    if buffer:
        yield buffer
