import html
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable

from .base import BaseExtractor, Document


class StackExchangeExtractor(BaseExtractor):
    source_name = "stackexchange"

    def __init__(self, posts_xml: str, comments_xml: str | None = None) -> None:
        self.posts_xml = Path(posts_xml)
        self.comments_xml = Path(comments_xml) if comments_xml else None

    def _load_comments(self) -> Dict[str, list[str]]:
        comments: Dict[str, list[str]] = {}
        if not self.comments_xml or not self.comments_xml.exists():
            return comments

        for _, elem in ET.iterparse(self.comments_xml, events=("end",)):
            if elem.tag != "row":
                continue
            post_id = elem.attrib.get("PostId")
            text = elem.attrib.get("Text", "")
            if post_id:
                comments.setdefault(post_id, []).append(html.unescape(text))
            elem.clear()
        return comments

    def stream(self) -> Iterable[Document]:
        comments = self._load_comments()
        questions = {}
        answers = {}

        for _, elem in ET.iterparse(self.posts_xml, events=("end",)):
            if elem.tag != "row":
                continue
            post_type = elem.attrib.get("PostTypeId")
            post_id = elem.attrib.get("Id")
            body = html.unescape(elem.attrib.get("Body", ""))
            title = html.unescape(elem.attrib.get("Title", ""))

            if post_type == "1" and post_id:
                questions[post_id] = {"title": title, "body": body}
            elif post_type == "2":
                parent_id = elem.attrib.get("ParentId")
                if parent_id:
                    answers.setdefault(parent_id, []).append(body)
            elem.clear()

        for qid, q in questions.items():
            merged = [q["title"], q["body"], *answers.get(qid, []), *comments.get(qid, [])]
            text = "\n\n".join(part for part in merged if part)
            if text:
                yield Document(
                    text=text,
                    meta={"source": self.source_name, "url": f"stackexchange://question/{qid}", "timestamp": None},
                )
