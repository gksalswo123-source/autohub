"""위비티 수집기 테스트. 인터넷 없이, 직접 만든 작은 HTML 샘플로 확인합니다."""

from autohub.cli import _filter
from autohub.sources.wevity import WevitySource

SAMPLE = """
<ul class="list">
  <li class="top"><div class="tit">공모전명</div><div class="organ">주최사</div></li>
  <li>
    <div class="tit">
      <a href="?c=find&s=1&gub=1&gbn=view&gp=1&ix=1001">대학생 AI 아이디어 공모전 <span class='stat spec'>SPECIAL</span></a>
      <div class="sub-tit">분야 : 기획/아이디어, 웹/모바일/IT</div>
    </div>
    <div class="organ">테스트재단</div>
    <div class="day">D-5 <span class="dday soon">마감임박</span></div>
    <div class="read">1,234</div>
  </li>
  <li class="bg">
    <div class="tit">
      <a href="?c=find&s=1&gub=1&gbn=view&gp=1&ix=1002">환경 사진 공모전</a>
      <div class="sub-tit">분야 : 영상/UCC/사진</div>
    </div>
    <div class="organ">그린협회</div>
    <div class="day">D-40 <span class="dday ing">접수중</span></div>
    <div class="read">99</div>
  </li>
</ul>
"""


def test_parse_reads_every_field():
    items = WevitySource().parse(SAMPLE)
    assert len(items) == 2

    first = items[0]
    assert first.id == "1001"
    assert first.title == "대학생 AI 아이디어 공모전"  # SPECIAL 배지는 빠져야 함
    assert first.url.startswith("https://www.wevity.com/")
    assert first.organizer == "테스트재단"
    assert first.categories == ["기획/아이디어", "웹/모바일/IT"]
    assert first.status == "마감임박"
    assert first.days_left == 5
    assert first.views == 1234


def test_filters():
    items = WevitySource().parse(SAMPLE)
    assert [c.id for c in _filter(items, "ai", None, None, False)] == ["1001"]
    assert [c.id for c in _filter(items, None, "사진", None, False)] == ["1002"]
    assert [c.id for c in _filter(items, None, None, 7, False)] == ["1001"]
