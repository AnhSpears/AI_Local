import re
import subprocess
from pathlib import Path
from typing import Iterable

from .base import BaseExtractor, Document


GUTENBERG_START_RE = re.compile(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG EBOOK .* \*\*\*")
GUTENBERG_END_RE = re.compile(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG EBOOK .* \*\*\*")


def mirror_gutenberg(destination_dir: str) -> None:
    Path(destination_dir).mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "rsync",
            "-avz",
            "--delete",
            "aleph.gutenberg.org::gutenberg",
            destination_dir,
        ],
        check=True,
    )


def strip_gutenberg_boilerplate(raw_text: str) -> str:
    lines = raw_text.splitlines()
    start_idx = 0
    end_idx = len(lines)

    for i, line in enumerate(lines):
        if GUTENBERG_START_RE.search(line.upper()):
            start_idx = i + 1
            break

    for i in range(len(lines) - 1, -1, -1):
        if GUTENBERG_END_RE.search(lines[i].upper()):
            end_idx = i
            break

    return "\n".join(lines[start_idx:end_idx]).strip()


class GutenbergExtractor(BaseExtractor):
    source_name = "gutenberg"

    def __init__(self, root_dir: str) -> None:
        self.root_dir = Path(root_dir)

    def stream(self) -> Iterable[Document]:
        for path in self.root_dir.rglob("*.txt"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            cleaned = strip_gutenberg_boilerplate(text)
            if cleaned:
                yield Document(
                    text=cleaned,
                    meta={"source": self.source_name, "url": str(path), "timestamp": None},
                )
