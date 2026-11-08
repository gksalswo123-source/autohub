"""`auto` 명령어의 입구입니다. 터미널에서 `auto --help` 로 사용법을 볼 수 있어요."""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import webbrowser
from datetime import date

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, drafts, storage, todoist
from .config import HOME_ENV, get_secret, save_secret
from .models import Contest
from .sources import SOURCES
from .sources.wevity import WevitySource

FREE_AI_URL = "https://claude.ai/new"

# 윈도우 터미널에서 한글·이모지가 깨지지 않도록
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

app = typer.Typer(help="AutoHub: 학업·업무·기획·공모전 자동화 도구", no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    """AutoHub 명령 모음."""


@app.command()
def version() -> None:
    """버전을 보여줍니다."""
    console.print(f"autohub {__version__}")


TOKEN_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


def read_clipboard_token() -> str | None:
    """클립보드에 Todoist 토큰(16진수 40자)이 복사돼 있으면 돌려줍니다."""
    text = ""
    try:
        if sys.platform == "win32":
            text = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=10, encoding="utf-8",
            ).stdout
        elif sys.platform == "darwin":
            text = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=10).stdout
        else:
            text = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=10
            ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    text = (text or "").strip()
    return text if TOKEN_PATTERN.match(text) else None


@app.command()
def setup() -> None:
    """Todoist 토큰을 저장합니다. 토큰을 '복사'만 해두고 실행하면 클립보드에서 읽어요."""
    token = read_clipboard_token()
    if token:
        console.print(f"클립보드에서 토큰을 찾았어요: [bold]{token[:4]}…{token[-4:]}[/bold]")
    else:
        console.print(
            "클립보드에 Todoist 토큰이 없어요.\n"
            "1) https://app.todoist.com/app/settings/integrations/developer 에서 [bold]API 토큰 복사[/bold] 버튼을 누르고\n"
            "2) [bold]auto setup[/bold] 을 다시 실행하세요. (붙여넣을 필요 없어요)"
        )
        raise typer.Exit(1)
    with console.status("[cyan]토큰 확인 중..."):
        try:
            projects = todoist.TodoistClient(token).list_projects()
        except Exception as error:
            console.print(f"[red]확인 실패: {error}[/red]\n저장하지 않았습니다. 토큰을 다시 복사해 보세요.")
            raise typer.Exit(1)
    path = save_secret("TODOIST_API_TOKEN", token)
    console.print(f"[green]연결 성공! (프로젝트 {len(projects)}개 확인)[/green] 저장 위치: {path}")
    console.print("이제 어느 폴더에서든 [bold]auto contests --todoist[/bold] 를 실행할 수 있어요.")


def parse_date(text: str, today: date | None = None) -> date:
    """'2026-12-01', '12-01', '12/1', '12.1', '12월 1일' 같은 날짜를 읽습니다.
    연도를 안 쓰면 올해로 보고, 이미 지난 날짜면 내년으로 봅니다."""
    today = today or date.today()
    numbers = [int(n) for n in re.findall(r"\d+", text)]
    if len(numbers) == 3:
        year, month, day = numbers
        if year < 100:
            year += 2000
        return date(year, month, day)
    if len(numbers) == 2:
        month, day = numbers
        result = date(today.year, month, day)
        return result if result >= today else date(today.year + 1, month, day)
    raise ValueError(f"날짜를 읽을 수 없어요: {text!r} (예: 12/1, 2026-12-01)")


@app.command()
def add(
    title: str = typer.Argument(..., help="대회/행사 이름 (띄어쓰기가 있으면 따옴표로 감싸기)"),
    when: str = typer.Option(..., "--date", "-d", help="마감일 또는 행사일 (예: 12/1, 2026-12-01)"),
    organizer: str = typer.Option("", "--organizer", "-o", help="주최/주관 (예: 영남대 무역학부)"),
    url: str = typer.Option("", "--url", "-u", help="공지 링크"),
    project: str = typer.Option("공모전", "--project", help="Todoist 프로젝트 이름"),
) -> None:
    """사이트에 없는 대회·행사(학과 행사 등)를 직접 Todoist에 추가합니다."""
    try:
        due = parse_date(when)
    except ValueError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(1)

    contest = Contest(
        source="manual",
        id=hashlib.sha1(f"{title}|{due.isoformat()}".encode()).hexdigest()[:10],
        title=title,
        url=url or "(링크 없음)",
        organizer=organizer,
        status="직접 추가",
        days_left=(due - date.today()).days,
    )
    console.print(f"[bold]{title}[/bold]  {due.isoformat()} (D-{contest.days_left})  {organizer}")
    _send_to_todoist([contest], project, yes=True)


def _make_draft(title: str, url: str, organizer: str, kind: str, memo: str, open_browser: bool) -> None:
    info: dict[str, str] = {}
    description = ""
    if url and "wevity.com" in url:
        with console.status("[cyan]공모 요강을 읽는 중..."):
            try:
                detail = WevitySource().fetch_detail(url)
            except Exception as error:
                console.print(f"[yellow]요강을 못 읽었어요({error}). 제목만으로 만들게요.[/yellow]")
            else:
                info, description = detail["info"], detail["description"]
                title = title or detail["title"]
                organizer = organizer or info.pop("주최/주관", "")

    if not title:
        console.print("[red]공모전 이름이나 --url 중 하나는 꼭 알려주세요.[/red]")
        raise typer.Exit(1)

    try:
        prompt = drafts.build_prompt(kind, title, organizer, info, description, memo)
    except ValueError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(1)

    path = drafts.save_draft(kind, title, prompt, source_url=url)
    console.print(f"[green]질문문 저장:[/green] {path}")

    if drafts.copy_to_clipboard(prompt):
        console.print("[green]질문문을 클립보드에 복사했어요.[/green]")
        console.print(f"👉 열린 AI 창에 [bold]Ctrl+V[/bold] 로 붙여넣고 Enter. 답변은 위 파일 '2. AI 답변'에 붙여 보관하세요.")
        if open_browser:
            webbrowser.open(FREE_AI_URL)
    else:
        console.print("[yellow]클립보드 복사에 실패했어요. 위 파일을 열어 '1. 질문문'을 복사해 주세요.[/yellow]")


@app.command()
def draft(
    title: str = typer.Argument(None, help="공모전 이름 (--url 을 주면 생략 가능)"),
    url: str = typer.Option("", "--url", "-u", help="공모전 상세 페이지 주소 (위비티면 요강을 자동으로 읽음)"),
    kind: str = typer.Option("아이디어", "--kind", "-k", help=f"만들 것: {', '.join(drafts.KINDS)}"),
    organizer: str = typer.Option("", "--organizer", "-o", help="주최/주관"),
    memo: str = typer.Option("", "--memo", "-m", help="우리 팀 정보 (예: 무역학부 3학년 2명, 데이터 분석 가능)"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="무료 AI(claude.ai) 창 자동으로 열기"),
) -> None:
    """[무료] 공모전 맞춤 아이디어·기획서·발표 질문문을 만들어 복사하고 AI 창을 엽니다."""
    _make_draft(title or "", url, organizer, kind, memo, open_browser)


def _filter(
    contests: list[Contest],
    keyword: str | None,
    category: str | None,
    days: int | None,
    only_open: bool,
) -> list[Contest]:
    result = []
    for c in contests:
        if keyword and keyword.lower() not in (c.title + " " + c.organizer).lower():
            continue
        if category and not any(category in cat for cat in c.categories):
            continue
        if days is not None and (c.days_left is None or c.days_left > days):
            continue
        if only_open and c.status == "접수예정":
            continue
        result.append(c)
    return result


def parse_selection(text: str, count: int) -> list[int]:
    """'1,3,5-7' 이나 'all' 같은 입력을 0부터 시작하는 번호 목록으로 바꿉니다."""
    text = text.strip().lower()
    if not text:
        return []
    if text in ("all", "a", "전부", "전체"):
        return list(range(count))
    picked: set[int] = set()
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            numbers = range(int(start), int(end) + 1)
        else:
            numbers = [int(part)]
        for n in numbers:
            if not 1 <= n <= count:
                raise ValueError(f"{n}번은 없습니다 (1~{count})")
            picked.add(n - 1)
    return sorted(picked)


def _send_to_todoist(items: list[Contest], project: str, yes: bool) -> None:
    token = get_secret("TODOIST_API_TOKEN")
    if not token:
        console.print(
            "[red]Todoist 토큰을 찾지 못했습니다.[/red] 먼저 [bold]auto setup[/bold] 을 실행해 토큰을 저장하세요.\n"
            f"(찾아본 곳: 지금 폴더의 .env, {HOME_ENV})"
        )
        raise typer.Exit(1)
    if not items:
        console.print("등록할 공모전이 없습니다.")
        return

    if yes:
        chosen = items
    else:
        while True:
            answer = typer.prompt(
                "Todoist에 추가할 번호 (예: 1,3,5-7 / all / 엔터=취소)", default="", show_default=False
            )
            try:
                chosen = [items[i] for i in parse_selection(answer, len(items))]
                break
            except ValueError as error:
                console.print(f"[red]{error}[/red] 다시 입력해 주세요.")
        if not chosen:
            console.print("취소했습니다.")
            return

    try:
        created, skipped = todoist.send(chosen, todoist.TodoistClient(token), project_name=project)
    except Exception as error:  # 토큰 오류, 인터넷 끊김 등
        console.print(f"[red]Todoist 등록 실패: {error}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Todoist '{project}' 프로젝트에 {len(created)}건 추가[/green]", end="")
    console.print(f" (이미 추가돼서 건너뜀 {len(skipped)}건)" if skipped else "")


@app.command()
def contests(
    pages: int = typer.Option(2, "--pages", "-p", help="몇 페이지까지 읽을지 (1페이지 ≈ 15~20건)"),
    keyword: str = typer.Option(None, "--keyword", "-k", help="제목/주최사에 들어간 단어로 거르기 (예: AI)"),
    category: str = typer.Option(None, "--category", "-c", help="분야로 거르기 (예: 기획, IT, 논문)"),
    days: int = typer.Option(None, "--days", "-d", help="마감이 N일 이내인 것만"),
    only_open: bool = typer.Option(False, "--open", help="지금 접수 중인 것만 (접수예정 제외)"),
    save: str = typer.Option(None, "--save", "-s", help="파일로 저장: csv, json, md, ics(캘린더)"),
    source: str = typer.Option("wevity", "--source", help=f"수집할 사이트: {', '.join(SOURCES)}"),
    to_todoist: bool = typer.Option(False, "--todoist", "-t", help="골라서 Todoist 할 일로 추가"),
    project: str = typer.Option("공모전", "--project", help="추가할 Todoist 프로젝트 이름 (없으면 만듦)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="묻지 않고 목록 전체를 추가 (자동 실행용)"),
    make_draft: bool = typer.Option(False, "--draft", help="하나를 골라 AI 초안 질문문 만들기 (무료)"),
    kind: str = typer.Option("아이디어", "--kind", help=f"--draft 로 만들 것: {', '.join(drafts.KINDS)}"),
) -> None:
    """공모전·대회 공고를 모아 마감일 순으로 보여줍니다."""
    if source not in SOURCES:
        console.print(f"[red]알 수 없는 사이트: {source}. 사용 가능: {', '.join(SOURCES)}[/red]")
        raise typer.Exit(1)

    with console.status(f"[cyan]{source}에서 공모전을 모으는 중..."):
        try:
            items = SOURCES[source]().collect(pages=pages)
        except Exception as error:  # 인터넷 끊김, 사이트 구조 변경 등
            console.print(f"[red]수집 실패: {error}[/red]")
            raise typer.Exit(1)

    new_count = storage.mark_new(items)
    items = _filter(items, keyword, category, days, only_open)
    items.sort(key=lambda c: (c.days_left is None, c.days_left if c.days_left is not None else 0))

    table = Table(title=f"공모전 {len(items)}건  (새로 올라온 것 {new_count}건)", show_lines=False)
    table.add_column("#", justify="right", style="dim")
    table.add_column("마감", justify="right", style="bold")
    table.add_column("상태")
    table.add_column("공모전", overflow="fold")
    table.add_column("주최", overflow="fold", max_width=18)

    for number, c in enumerate(items, start=1):
        dday = f"D-{c.days_left}" if c.days_left is not None else "-"
        color = "red" if c.days_left is not None and c.days_left <= 7 else "green"
        title = f"[link={c.url}]{c.title}[/link]"
        if c.is_new:
            title = "[yellow]NEW[/yellow] " + title
        table.add_row(str(number), f"[{color}]{dday}[/{color}]", c.status, title, c.organizer)

    console.print(table)

    if save:
        try:
            path = storage.save(items, save.lower())
        except ValueError as error:
            console.print(f"[red]{error}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]저장 완료:[/green] {path}")

    if to_todoist:
        _send_to_todoist(items, project, yes)

    if make_draft and items:
        while True:
            answer = typer.prompt("초안을 만들 공모전 번호 1개 (엔터=취소)", default="", show_default=False)
            if not answer.strip():
                console.print("취소했습니다.")
                return
            try:
                picked = parse_selection(answer, len(items))
            except ValueError as error:
                console.print(f"[red]{error}[/red]")
                continue
            if len(picked) == 1:
                break
            console.print("[red]번호는 1개만 골라 주세요.[/red]")
        chosen = items[picked[0]]
        _make_draft(chosen.title, chosen.url, chosen.organizer, kind, "", True)


if __name__ == "__main__":
    app()
