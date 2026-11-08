"""공모전 사이트별 수집기 목록.

새 사이트를 추가하려면:
1. 이 폴더에 `사이트이름.py` 를 만들고 BaseSource 를 상속한 클래스를 작성
2. 아래 SOURCES 딕셔너리에 한 줄 추가
"""

from .base import BaseSource
from .wevity import WevitySource

SOURCES: dict[str, type[BaseSource]] = {
    WevitySource.name: WevitySource,
}

__all__ = ["BaseSource", "SOURCES"]
