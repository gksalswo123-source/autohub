"""모든 수집기가 공통으로 쓰는 데이터 모양(공모전 한 건)을 정의합니다."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta


@dataclass
class Contest:
    source: str                 # 어느 사이트에서 왔는지 (예: "wevity")
    id: str                     # 사이트 안에서의 고유 번호
    title: str                  # 공모전 이름
    url: str                    # 상세 페이지 주소
    organizer: str = ""         # 주최사
    categories: list[str] = field(default_factory=list)  # 분야
    status: str = ""            # 접수중 / 마감임박 / 접수예정 등
    days_left: int | None = None  # 사이트에 표시된 D-day 숫자
    views: int | None = None    # 조회수
    is_new: bool = False        # 지난번 실행 이후 처음 본 공모전인지

    @property
    def key(self) -> str:
        """사이트가 달라도 겹치지 않는 고유 키."""
        return f"{self.source}:{self.id}"

    @property
    def deadline(self) -> date | None:
        """D-day 숫자로 계산한 대략적인 마감일."""
        if self.days_left is None:
            return None
        return date.today() + timedelta(days=self.days_left)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["deadline"] = self.deadline.isoformat() if self.deadline else None
        return data
