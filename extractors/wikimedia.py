import bz2
import xml.etree.ElementTree as ET
from typing import Iterable

import mwparserfromhell

from .base import BaseExtractor, Document


class WikimediaDumpExtractor(BaseExtractor):
    source_name = "wikimedia"

    def __init__(self, xml_bz2_path: str) -> None:
        self.xml_bz2_path = xml_bz2_path

    def stream(self) -> Iterable[Document]:
        context = ET.iterparse(bz2.open(self.xml_bz2_path, "rb"), events=("end",))
        for _, elem in context:
            if not elem.tag.endswith("page"):
                continue

            title = ""
            text = ""
            for child in elem.iter():
                if child.tag.endswith("title") and child.text:
                    title = child.text
                if child.tag.endswith("text") and child.text:
                    text = child.text

            if text:
                plain = mwparserfromhell.parse(text).strip_code(normalize=True, collapse=True)
                yield Document(
                    text=f"{title}\n\n{plain}",
                    meta={"source": self.source_name, "url": title, "timestamp": None},
                )
            elem.clear()
