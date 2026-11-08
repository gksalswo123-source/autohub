"""위비티(wevity.com) 공모전 목록 수집기."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from ..models import Contest
from .base import BaseSource

BASE_URL = "https://www.wevity.com/"


class WevitySource(BaseSource):
    name = "wevity"

    def page_url(self, page: int) -> str:
        return f"{BASE_URL}?c=find&s=1&gub=1&gp={page}"

    def fetch_detail(self, url: str) -> dict:
        return parse_detail(self.fetch_html(url))

    def parse(self, html: str) -> list[Contest]:
        soup = BeautifulSoup(html, "html.parser")
        contests: list[Contest] = []

        # 목록은 <ul class="list"> 안의 <li> 들이고, 첫 줄(class="top")은 제목행입니다.
        for li in soup.select("ul.list > li"):
            if "top" in (li.get("class") or []):
                continue
            link = li.select_one("div.tit > a")
            if link is None or not link.get("href"):
                continue

            href = urljoin(BASE_URL, link["href"])
            contest_id = parse_qs(urlparse(href).query).get("ix", [href])[0]

            # 제목 옆의 SPECIAL / IDEA 같은 배지는 빼고 순수 제목만 남깁니다.
            for badge in link.select("span"):
                badge.decompose()
            title = " ".join(link.get_text().split())

            sub = li.select_one("div.sub-tit")
            categories: list[str] = []
            if sub:
                text = sub.get_text(strip=True).removeprefix("분야 :").strip()
                categories = [c.strip() for c in text.split(",") if c.strip()]

            organ = li.select_one("div.organ")
            day = li.select_one("div.day")
            status_tag = day.select_one("span.dday") if day else None
            day_text = day.get_text(" ", strip=True) if day else ""
            match = re.search(r"D-(\d+)", day_text)
            if match:
                days_left = int(match.group(1))
            elif "D-day" in day_text or "D-Day" in day_text:
                days_left = 0
            else:
                days_left = None

            read = li.select_one("div.read")
            views_text = read.get_text(strip=True).replace(",", "") if read else ""

            contests.append(
                Contest(
                    source=self.name,
                    id=contest_id,
                    title=title,
                    url=href,
                    organizer=organ.get_text(strip=True) if organ else "",
                    categories=categories,
                    status=status_tag.get_text(strip=True) if status_tag else "",
                    days_left=days_left,
                    views=int(views_text) if views_text.isdigit() else None,
                )
            )
        return contests


def parse_detail(html: str) -> dict:
    """상세 페이지에서 {"title", "info": {항목: 값}, "description"} 을 뽑아냅니다."""
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.select_one("div.tit-area h6.tit")

    info: dict[str, str] = {}
    for li in soup.select("ul.cd-info-list > li"):
        label_tag = li.select_one("span.tit")
        label = label_tag.get_text(strip=True) if label_tag else ""
        if not label:
            continue
        label_tag.decompose()
        for extra in li.select("span.cil-dday, script"):
            extra.decompose()
        value = " ".join(li.get_text(" ", strip=True).split())
        if value:
            info[label] = value

    desc_tag = soup.select_one("#viewContents")
    description = ""
    if desc_tag:
        lines = [" ".join(line.split()) for line in desc_tag.get_text("\n").splitlines()]
        description = "\n".join(line for line in lines if line)

    return {
        "title": title_tag.get_text(strip=True) if title_tag else "",
        "info": info,
        "description": description,
    }
