import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, List

import requests

from .base import BaseExtractor, Document


class PubMedEntrezExtractor(BaseExtractor):
    source_name = "pubmed"
    EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, pmc_ids: List[str]) -> None:
        self.pmc_ids = pmc_ids

    def stream(self) -> Iterable[Document]:
        for pmc_id in self.pmc_ids:
            params = {"db": "pmc", "id": pmc_id, "retmode": "xml"}
            resp = requests.get(self.EUTILS_URL, params=params, timeout=60)
            resp.raise_for_status()
            for doc in parse_jats_xml(resp.text):
                doc.meta["url"] = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/"
                yield doc


class PubMedBulkExtractor(BaseExtractor):
    source_name = "pubmed"

    def __init__(self, xml_dir: str) -> None:
        self.xml_dir = Path(xml_dir)

    def stream(self) -> Iterable[Document]:
        for path in self.xml_dir.rglob("*.xml"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for doc in parse_jats_xml(text):
                doc.meta["url"] = str(path)
                yield doc


def _collect_text(nodes: Iterable[ET.Element]) -> str:
    parts = []
    for node in nodes:
        parts.append(" ".join(fragment.strip() for fragment in node.itertext() if fragment.strip()))
    return "\n".join(part for part in parts if part)


def parse_jats_xml(xml_text: str) -> Iterable[Document]:
    root = ET.fromstring(xml_text)
    for article in root.findall(".//article"):
        abstract = _collect_text(article.findall(".//abstract"))
        body = _collect_text(article.findall(".//body"))
        concl = _collect_text(article.findall(".//sec[title='Conclusion']"))
        joined = "\n\n".join([part for part in [abstract, body, concl] if part])
        if not joined.strip():
            continue
        yield Document(
            text=joined,
            meta={"source": "pubmed", "url": "", "timestamp": None},
        )
