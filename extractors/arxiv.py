import io
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, Optional

import pdfplumber
import requests

from .base import BaseExtractor, Document


class ArxivAPIExtractor(BaseExtractor):
    source_name = "arxiv"
    API_URL = "http://export.arxiv.org/api/query"

    def __init__(self, search_query: str = "cat:cs.CL", start: int = 0, max_results: int = 100) -> None:
        self.search_query = search_query
        self.start = start
        self.max_results = max_results

    def stream(self) -> Iterable[Document]:
        params = {
            "search_query": self.search_query,
            "start": self.start,
            "max_results": self.max_results,
        }
        response = requests.get(self.API_URL, params=params, timeout=60)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
            arxiv_id = entry.findtext("atom:id", default="", namespaces=ns)
            published = entry.findtext("atom:published", default="", namespaces=ns)
            yield Document(
                text=f"{title}\n\n{summary}",
                meta={"source": self.source_name, "url": arxiv_id, "timestamp": published},
            )


def extract_text_from_latex(tex_content: str) -> str:
    """Lightweight LaTeX cleanup for pretraining text extraction."""
    remove_cmds = [r"\\begin{figure}", r"\\end{figure}", r"\\begin{table}", r"\\end{table}"]
    text = tex_content
    for marker in remove_cmds:
        text = text.replace(marker, " ")
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("%"))


def extract_text_from_pdf(pdf_path: str) -> str:
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


class ArxivBulkTarExtractor(BaseExtractor):
    source_name = "arxiv"

    def __init__(self, tar_path: str) -> None:
        self.tar_path = Path(tar_path)

    def stream(self) -> Iterable[Document]:
        with tarfile.open(self.tar_path, mode="r|*") as tar:
            for member in tar:
                if not member.isfile():
                    continue
                if not member.name.endswith((".tex", ".txt")):
                    continue
                f = tar.extractfile(member)
                if f is None:
                    continue
                text = f.read().decode("utf-8", errors="ignore")
                yield Document(
                    text=extract_text_from_latex(text),
                    meta={"source": self.source_name, "url": member.name, "timestamp": None},
                )
