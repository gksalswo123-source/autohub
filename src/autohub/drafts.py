"""무료로 쓰는 AI 초안 도우미.

API 키 없이, 공모전 정보를 담은 '질문문(프롬프트)'을 만들어 클립보드에 복사합니다.
그걸 claude.ai 같은 무료 AI 웹사이트에 붙여넣으면 초안이 나옵니다.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

MAX_DESCRIPTION = 6000  # 요강이 너무 길면 AI 입력창에 안 들어가니 자릅니다.

COMMON_RULES = """\
작성 규칙:
- 한국어로, 심사위원이 읽기 쉽게 소제목과 글머리표를 사용해 주세요.
- 통계·수치·사례는 지어내지 말고, 필요한 곳에 [확인 필요: 찾아야 할 자료] 라고 표시해 주세요.
- 공모전 요강의 주제·참가자격·제출 형식·평가 기준을 반드시 지켜 주세요.
- 마지막에 '제출 전 체크리스트'(분량, 형식, 마감일 등)를 5줄 이내로 붙여 주세요."""

KINDS: dict[str, str] = {
    "아이디어": """\
위 공모전에 낼 아이디어를 5개 제안해 주세요. 각 아이디어마다:
1. 한 줄 제목
2. 해결하려는 문제 (누가, 왜 불편한가)
3. 해결 방법 (핵심 기능/방식)
4. 기존 사례와의 차별점
5. 대학생 팀이 마감 안에 할 수 있는지 (실현 가능성 상/중/하와 이유)
6. 예상 평가 기준별 강점
마지막에 수상 가능성이 가장 높은 1개를 고르고 이유를 3줄로 설명해 주세요.""",
    "기획서": """\
위 공모전에 제출할 기획서 초안을 작성해 주세요. 목차:
1. 제목과 한 줄 요약
2. 추진 배경 및 문제 정의
3. 목표 (정량 목표 포함)
4. 핵심 아이디어와 차별성
5. 세부 실행 방안 (단계별 내용, 일정표)
6. 필요 자원 및 예산 (해당 시)
7. 기대 효과 (정량·정성)
8. 예상 위험과 대응 방안
요강에 정해진 양식이 있으면 그 양식의 항목 순서를 우선해 주세요.""",
    "발표": """\
위 공모전 본선 발표(5분)를 준비해 주세요.
1. 슬라이드 10장 구성 (장마다 제목 + 핵심 문장 1개 + 넣을 시각자료)
2. 장별 발표 대본 (총 5분 분량, 말하듯 자연스럽게)
3. 심사위원 예상 질문 7개와 모범 답변
4. 발표 시간 배분표""",
}


def build_prompt(
    kind: str,
    title: str,
    organizer: str = "",
    info: dict[str, str] | None = None,
    description: str = "",
    memo: str = "",
) -> str:
    if kind not in KINDS:
        raise ValueError(f"종류는 {', '.join(KINDS)} 중 하나여야 해요.")

    parts = ["당신은 대학생 공모전 수상 경험이 많은 기획 멘토입니다.", "", "## 공모전 정보", f"- 이름: {title}"]
    if organizer:
        parts.append(f"- 주최/주관: {organizer}")
    for label, value in (info or {}).items():
        if label in ("첨부파일", "홈페이지") and value in ("파일없음", ""):
            continue
        parts.append(f"- {label}: {value}")

    if description:
        text = description if len(description) <= MAX_DESCRIPTION else description[:MAX_DESCRIPTION] + "\n…(이하 생략)"
        parts += ["", "## 공모 요강 (원문)", text]

    if memo:
        parts += ["", "## 우리 팀 정보", memo]

    parts += ["", "## 요청", KINDS[kind], "", COMMON_RULES]
    return "\n".join(parts)


def slugify(text: str, limit: int = 40) -> str:
    """파일 이름에 쓸 수 없는 글자를 빼고 짧게 줄입니다."""
    text = re.sub(r'[\\/:*?"<>|\[\]]+', " ", text)
    text = "_".join(text.split())
    return text[:limit].rstrip("_") or "draft"


def save_draft(kind: str, title: str, prompt: str, source_url: str = "", output_dir: Path = Path("output") / "drafts") -> Path:
    """질문문을 마크다운 파일로 저장합니다. AI 답변을 받아 아래에 붙여넣어 보관하세요."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{date.today().isoformat()}_{slugify(title)}_{kind}.md"
    body = [
        f"# {title} — {kind} 초안",
        "",
        f"- 만든 날: {date.today().isoformat()}",
    ]
    if source_url:
        body.append(f"- 원문: {source_url}")
    body += [
        "",
        "## 1. AI에게 보낸 질문문",
        "",
        "````text",
        prompt,
        "````",
        "",
        "## 2. AI 답변 (여기에 붙여넣기)",
        "",
        "",
        "## 3. 내가 고칠 점 / 메모",
        "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")
    return path


def copy_to_clipboard(text: str) -> bool:
    """텍스트를 클립보드에 복사합니다. 성공하면 True."""
    try:
        if sys.platform == "win32":
            # 한글이 깨지지 않도록 UTF-8 파일을 거쳐 PowerShell 로 복사합니다.
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
                f.write(text)
                temp_path = f.name
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"Get-Content -Raw -Encoding UTF8 -LiteralPath '{temp_path}' | Set-Clipboard"],
                    capture_output=True, timeout=15,
                )
            finally:
                Path(temp_path).unlink(missing_ok=True)
            return result.returncode == 0
        command = ["pbcopy"] if sys.platform == "darwin" else ["xclip", "-selection", "clipboard"]
        return subprocess.run(command, input=text.encode("utf-8"), timeout=15).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
