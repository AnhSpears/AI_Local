import base64
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from github import Github

from .base import BaseExtractor, Document


OPEN_LICENSE_KEYWORDS = ("mit", "apache", "bsd", "mpl", "isc")
CODE_EXTENSIONS = {".py", ".js", ".ts", ".cpp", ".c", ".h", ".java", ".go", ".rs"}


def bigquery_example_sql() -> str:
    return """
    SELECT repo_name
    FROM `bigquery-public-data.github_repos.licenses`
    WHERE LOWER(license) IN ('mit', 'apache-2.0', 'bsd-3-clause')
    LIMIT 10000;
    """.strip()


class GitHubAPIExtractor(BaseExtractor):
    source_name = "github"

    def __init__(self, token: str, repos: Sequence[str]) -> None:
        self.client = Github(token)
        self.repos = repos

    def _is_open_license(self, repo) -> bool:
        license_name = (repo.get_license().license.spdx_id or "").lower() if repo.get_license() else ""
        return any(k in license_name for k in OPEN_LICENSE_KEYWORDS)

    def _iter_repo_files(self, repo) -> Iterator[Document]:
        queue = repo.get_contents("")
        while queue:
            file_content = queue.pop(0)
            if file_content.type == "dir":
                queue.extend(repo.get_contents(file_content.path))
                continue
            ext = Path(file_content.path).suffix.lower()
            if ext not in CODE_EXTENSIONS:
                continue
            if not file_content.content:
                blob = repo.get_git_blob(file_content.sha)
                text = base64.b64decode(blob.content).decode("utf-8", errors="ignore")
            else:
                text = base64.b64decode(file_content.content).decode("utf-8", errors="ignore")
            yield Document(
                text=text,
                meta={
                    "source": self.source_name,
                    "url": file_content.html_url,
                    "timestamp": None,
                },
            )

    def stream(self) -> Iterable[Document]:
        for full_name in self.repos:
            repo = self.client.get_repo(full_name)
            if not self._is_open_license(repo):
                continue
            yield from self._iter_repo_files(repo)
