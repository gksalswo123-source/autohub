"""공모전을 Todoist 할 일로 등록합니다.

Todoist API 문서: https://developer.todoist.com/api/v1/
토큰 발급: Todoist 웹 → 설정 → 연동 서비스(Integrations) → 개발자(Developer) → API 토큰
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

from .config import DATA_DIR
from .models import Contest

API_BASE = "https://api.todoist.com/api/v1"
ADDED_FILE = DATA_DIR / "todoist_added.json"


class TodoistError(Exception):
    pass


class TodoistClient:
    def __init__(self, token: str, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _request(self, method: str, path: str, **kwargs) -> object:
        response = self.session.request(method, f"{API_BASE}{path}", timeout=15, **kwargs)
        if response.status_code in (401, 403):
            raise TodoistError("토큰이 올바르지 않습니다. .env 의 TODOIST_API_TOKEN 을 확인하세요.")
        if response.status_code >= 400:
            raise TodoistError(f"Todoist 오류 {response.status_code}: {response.text[:200]}")
        return response.json() if response.content else None

    def list_projects(self) -> list[dict]:
        """모든 프로젝트를 가져옵니다. (여러 페이지로 나뉘어 와도 모두 모읍니다)"""
        projects: list[dict] = []
        cursor = None
        while True:
            params = {"cursor": cursor} if cursor else {}
            data = self._request("GET", "/projects", params=params)
            if isinstance(data, list):  # 페이지 구분 없이 목록만 오는 경우
                return data
            projects.extend(data.get("results", []))
            cursor = data.get("next_cursor")
            if not cursor:
                return projects

    def get_or_create_project(self, name: str) -> str:
        for project in self.list_projects():
            if project.get("name") == name:
                return str(project["id"])
        created = self._request("POST", "/projects", json={"name": name})
        return str(created["id"])

    def add_task(self, payload: dict) -> str:
        created = self._request("POST", "/tasks", json=payload)
        return str(created["id"])


def task_payload(contest: Contest, project_id: str) -> dict:
    """공모전 한 건 → Todoist 할 일 데이터."""
    lines = [contest.url] if contest.url.startswith("http") else []
    if contest.organizer:
        lines.append(f"주최: {contest.organizer}")
    if contest.categories:
        lines.append(f"분야: {', '.join(contest.categories)}")
    lines.append(f"상태: {contest.status} (autohub 수집)")

    payload = {
        "content": f"[공모전] {contest.title}",
        "description": "\n".join(lines),
        "project_id": project_id,
        "labels": ["공모전"],
        # Todoist 우선순위: 4가 가장 높음(빨강), 1이 보통
        "priority": 4 if (contest.days_left is not None and contest.days_left <= 3)
        else 3 if (contest.days_left is not None and contest.days_left <= 7) else 1,
    }
    if contest.deadline:
        payload["due_date"] = contest.deadline.isoformat()
    return payload


def _load_added(path: Path) -> dict[str, str]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def send(
    contests: list[Contest],
    client: TodoistClient,
    project_name: str = "공모전",
    added_file: Path = ADDED_FILE,
) -> tuple[list[Contest], list[Contest]]:
    """할 일로 등록하고 (새로 등록한 것, 이미 등록돼서 건너뛴 것) 을 돌려줍니다."""
    added = _load_added(added_file)
    project_id = client.get_or_create_project(project_name)

    created: list[Contest] = []
    skipped: list[Contest] = []
    try:
        for contest in contests:
            if contest.key in added:
                skipped.append(contest)
                continue
            added[contest.key] = client.add_task(task_payload(contest, project_id))
            created.append(contest)
    finally:
        # 중간에 실패해도 그때까지 등록한 건 기록해서, 다음에 중복 등록되지 않게 합니다.
        added_file.parent.mkdir(parents=True, exist_ok=True)
        added_file.write_text(json.dumps(added, ensure_ascii=False, indent=2), encoding="utf-8")
    return created, skipped
