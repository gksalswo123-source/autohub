"""Todoist 연동 테스트. 진짜 Todoist 대신 가짜 서버(FakeSession)를 씁니다."""

import json

import pytest

from autohub import todoist
from autohub.cli import parse_selection
from autohub.models import Contest
from autohub.storage import to_ics


class FakeResponse:
    def __init__(self, status: int, data):
        self.status_code = status
        self._data = data
        self.content = json.dumps(data).encode()
        self.text = json.dumps(data)

    def json(self):
        return self._data


class FakeSession:
    """Todoist API 흉내: 프로젝트 목록 / 프로젝트 생성 / 할 일 생성."""

    def __init__(self, projects=None, status=200):
        self.headers = {}
        self.projects = projects or []
        self.tasks = []
        self.status = status

    def request(self, method, url, **kwargs):
        if self.status != 200:
            return FakeResponse(self.status, {"error": "nope"})
        if method == "GET" and url.endswith("/projects"):
            return FakeResponse(200, {"results": self.projects, "next_cursor": None})
        if method == "POST" and url.endswith("/projects"):
            project = {"id": "p-new", "name": kwargs["json"]["name"]}
            self.projects.append(project)
            return FakeResponse(200, project)
        if method == "POST" and url.endswith("/tasks"):
            task = {"id": f"t{len(self.tasks) + 1}", **kwargs["json"]}
            self.tasks.append(task)
            return FakeResponse(200, task)
        raise AssertionError(f"예상 못한 요청 {method} {url}")


def make(id_, days):
    return Contest(source="wevity", id=id_, title=f"공모전 {id_}", url=f"https://x/{id_}",
                   organizer="주최", categories=["기획/아이디어"], status="접수중", days_left=days)


def test_send_creates_project_and_tasks_without_duplicates(tmp_path):
    session = FakeSession()
    client = todoist.TodoistClient("fake-token", session=session)
    added_file = tmp_path / "added.json"

    created, skipped = todoist.send([make("1", 2), make("2", 30)], client, added_file=added_file)
    assert [c.id for c in created] == ["1", "2"] and skipped == []
    assert session.headers["Authorization"] == "Bearer fake-token"
    assert session.projects[0]["name"] == "공모전"

    first = session.tasks[0]
    assert first["project_id"] == "p-new"
    assert first["content"] == "[공모전] 공모전 1"
    assert first["priority"] == 4  # 마감 3일 이내 → 가장 높은 우선순위
    assert "due_date" in first and "https://x/1" in first["description"]

    # 두 번째 실행: 이미 넣은 건 다시 넣지 않음
    created, skipped = todoist.send([make("1", 2), make("3", 5)], client, added_file=added_file)
    assert [c.id for c in created] == ["3"] and [c.id for c in skipped] == ["1"]
    assert len(session.tasks) == 3


def test_existing_project_is_reused(tmp_path):
    session = FakeSession(projects=[{"id": "p1", "name": "공모전"}])
    client = todoist.TodoistClient("t", session=session)
    todoist.send([make("1", 10)], client, added_file=tmp_path / "a.json")
    assert len(session.projects) == 1 and session.tasks[0]["project_id"] == "p1"


def test_bad_token_gives_friendly_error(tmp_path):
    client = todoist.TodoistClient("bad", session=FakeSession(status=401))
    with pytest.raises(todoist.TodoistError, match="토큰"):
        todoist.send([make("1", 1)], client, added_file=tmp_path / "a.json")


def test_parse_selection():
    assert parse_selection("1,3,5-6", 6) == [0, 2, 4, 5]
    assert parse_selection("all", 3) == [0, 1, 2]
    assert parse_selection("", 3) == []
    with pytest.raises(ValueError):
        parse_selection("9", 3)


def test_ics_has_event_and_alarm():
    text = to_ics([make("1", 10), make("2", None)])
    assert text.count("BEGIN:VEVENT") == 1  # 마감일 없는 건 제외
    assert "TRIGGER:-P3D" in text and "UID:wevity-1@autohub" in text
