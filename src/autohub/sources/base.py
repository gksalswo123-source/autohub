"""모든 수집기의 공통 부모 클래스."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

import requests

from ..models import Contest

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 autohub/0.1"
)


class BaseSource(ABC):
    name: str = "base"
    delay_seconds: float = 1.5  # 사이트에 부담을 주지 않도록 페이지 사이에 쉬는 시간

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def fetch_html(self, url: str) -> str:
        response = self.session.get(url, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        return response.text

    def collect(self, pages: int = 1) -> list[Contest]:
        """여러 페이지를 차례로 읽어 공모전 목록을 돌려줍니다."""
        results: list[Contest] = []
        for page in range(1, pages + 1):
            if page > 1:
                time.sleep(self.delay_seconds)
            html = self.fetch_html(self.page_url(page))
            items = self.parse(html)
            if not items:
                break
            results.extend(items)
        return results

    @abstractmethod
    def page_url(self, page: int) -> str:
        """n번째 목록 페이지의 주소."""

    @abstractmethod
    def parse(self, html: str) -> list[Contest]:
        """목록 페이지 HTML에서 공모전들을 뽑아냅니다."""
