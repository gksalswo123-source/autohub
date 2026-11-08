"""결과를 파일로 저장하고, '새로 올라온 공모전'을 알아내기 위해 기록을 남깁니다."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .config import DATA_DIR
from .models import Contest

OUTPUT_DIR = Path("output")
SEEN_FILE = DATA_DIR / "seen_contests.json"


def mark_new(contests: list[Contest], seen_file: Path = SEEN_FILE) -> int:
    """이전에 본 적 없는 공모전에 is_new=True 를 표시하고, 그 개수를 돌려줍니다."""
    seen: set[str] = set()
    first_run = not seen_file.exists()
    if not first_run:
        seen = set(json.loads(seen_file.read_text(encoding="utf-8")))

    new_count = 0
    for contest in contests:
        if contest.key not in seen:
            contest.is_new = not first_run  # 처음 실행 때는 전부 NEW 로 표시하지 않음
            new_count += contest.is_new
            seen.add(contest.key)

    seen_file.parent.mkdir(parents=True, exist_ok=True)
    seen_file.write_text(json.dumps(sorted(seen), ensure_ascii=False), encoding="utf-8")
    return new_count


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def to_ics(contests: list[Contest], remind_days: int = 3) -> str:
    """캘린더 파일(.ics) 내용을 만듭니다. 마감일에 종일 일정 + N일 전 알림."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//autohub//contests//KO",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:공모전 마감",
    ]
    for c in contests:
        if not c.deadline:
            continue
        start = c.deadline.strftime("%Y%m%d")
        end = (c.deadline + timedelta(days=1)).strftime("%Y%m%d")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{c.source}-{c.id}@autohub",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{start}",
            f"DTEND;VALUE=DATE:{end}",
            f"SUMMARY:{_ics_escape('[마감] ' + c.title)}",
            f"DESCRIPTION:{_ics_escape(f'주최: {c.organizer}' + chr(10) + c.url)}",
            f"URL:{c.url}",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_ics_escape(c.title + ' 마감 ' + str(remind_days) + '일 전')}",
            f"TRIGGER:-P{remind_days}D",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def save(contests: list[Contest], fmt: str, output_dir: Path = OUTPUT_DIR) -> Path:
    """csv / json / md / ics 중 하나로 저장하고 파일 경로를 돌려줍니다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"contests_{date.today().isoformat()}.{fmt}"
    rows = [c.to_dict() for c in contests]

    if fmt == "json":
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    elif fmt == "csv":
        # utf-8-sig: 엑셀에서 열어도 한글이 깨지지 않습니다.
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["title"])
            writer.writeheader()
            for row in rows:
                row["categories"] = ", ".join(row["categories"])
                writer.writerow(row)
    elif fmt == "md":
        lines = [
            f"# 공모전 목록 ({date.today().isoformat()})",
            "",
            "| 마감 | 상태 | 공모전 | 주최 | 분야 |",
            "|---|---|---|---|---|",
        ]
        for c in contests:
            dday = f"D-{c.days_left}" if c.days_left is not None else "-"
            new = "🆕 " if c.is_new else ""
            title = c.title.replace("|", "\\|")
            lines.append(
                f"| {dday} | {c.status} | {new}[{title}]({c.url}) | {c.organizer} | {', '.join(c.categories)} |"
            )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif fmt == "ics":
        path.write_bytes(to_ics(contests).encode("utf-8"))
    else:
        raise ValueError(f"지원하지 않는 형식입니다: {fmt}")
    return path
