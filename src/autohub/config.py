"""API 키 같은 비밀 값과 기록 파일의 위치를 관리합니다. (추가 라이브러리 없이)

어느 폴더에서 `auto` 를 실행해도 같은 설정을 쓰도록, 기본 위치는 홈 폴더의 `.autohub` 입니다.
  - 윈도우: C:\\Users\\내이름\\.autohub\\.env
  - 맥/리눅스: ~/.autohub/.env
지금 폴더에 `.env` 가 있으면 그것을 먼저 읽습니다.
"""

from __future__ import annotations

import os
from pathlib import Path

HOME_DIR = Path(os.environ.get("AUTOHUB_HOME", Path.home() / ".autohub"))
HOME_ENV = HOME_DIR / ".env"
DATA_DIR = HOME_DIR / "data"


def load_env(paths: tuple[Path, ...] | None = None) -> None:
    """`.env` 의 `이름=값` 줄들을 환경 변수로 등록합니다. 먼저 읽은 값이 우선이에요."""
    for path in paths or (Path(".env"), HOME_ENV):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            if value:
                os.environ.setdefault(name.strip(), value)


def get_secret(name: str) -> str | None:
    load_env()
    value = os.environ.get(name, "").strip()
    return value or None


def save_secret(name: str, value: str, path: Path = HOME_ENV) -> Path:
    """`.env` 에 `이름=값` 을 저장합니다. 같은 이름이 있으면 바꿔 씁니다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
    lines = [line for line in lines if not line.strip().startswith(f"{name}=")]
    lines.append(f"{name}={value.strip()}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[name] = value.strip()
    return path
