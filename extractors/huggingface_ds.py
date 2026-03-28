from typing import Iterable, Optional

from datasets import load_dataset

from .base import BaseExtractor, Document


class HuggingFaceStreamingExtractor(BaseExtractor):
    source_name = "huggingface"

    def __init__(
        self,
        dataset_name: str,
        split: str = "train",
        text_field: str = "text",
        name: Optional[str] = None,
    ) -> None:
        self.dataset_name = dataset_name
        self.name = name
        self.split = split
        self.text_field = text_field

    def stream(self) -> Iterable[Document]:
        ds = load_dataset(self.dataset_name, self.name, split=self.split, streaming=True)
        for row in ds:
            text = row.get(self.text_field)
            if not text:
                continue
            yield Document(
                text=str(text),
                meta={
                    "source": self.source_name,
                    "url": f"hf://{self.dataset_name}/{self.split}",
                    "timestamp": None,
                },
            )
