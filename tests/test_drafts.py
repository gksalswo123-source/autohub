"""무료 AI 초안(질문문) 테스트."""

import pytest

from autohub import drafts
from autohub.sources.wevity import parse_detail

DETAIL = """
<div class="tit-area"><h6 class="tit">대학생 AI 아이디어 공모전</h6></div>
<ul class="cd-info-list">
  <li><span class="tit">분야</span> 기획/아이디어, 웹/모바일/IT </li>
  <li><span class="tit">응모대상</span> 대학생 </li>
  <li><span class="tit">주최/주관</span> 테스트재단 </li>
  <li class="dday-area"><span class="tit">접수기간</span> 2026-11-01 ~ 2026-12-01 <span class="cil-dday">D-23</span></li>
  <li><span class="tit">첨부파일</span> 파일없음 </li>
  <li class="sns"><span class="tit"></span><div>공유</div></li>
</ul>
<div class="comm-desc" id="viewContents"><div>■ 주제 : 생활 속 AI</div><div><br></div><div>■ 시상 : 대상 100만원</div></div>
"""


def test_parse_detail():
    detail = parse_detail(DETAIL)
    assert detail["title"] == "대학생 AI 아이디어 공모전"
    assert detail["info"]["접수기간"] == "2026-11-01 ~ 2026-12-01"  # D-day 표시는 빠짐
    assert detail["info"]["주최/주관"] == "테스트재단"
    assert "" not in detail["info"]  # 이름 없는 공유 버튼 줄은 무시
    assert detail["description"] == "■ 주제 : 생활 속 AI\n■ 시상 : 대상 100만원"


@pytest.mark.parametrize("kind", list(drafts.KINDS))
def test_build_prompt_has_everything(kind):
    detail = parse_detail(DETAIL)
    prompt = drafts.build_prompt(kind, detail["title"], "테스트재단", detail["info"],
                                 detail["description"], memo="무역학부 3학년 2명")
    assert "대학생 AI 아이디어 공모전" in prompt
    assert "생활 속 AI" in prompt and "무역학부 3학년 2명" in prompt
    assert drafts.KINDS[kind] in prompt and "[확인 필요" in prompt
    assert "파일없음" not in prompt


def test_unknown_kind():
    with pytest.raises(ValueError):
        drafts.build_prompt("시", "제목")


def test_long_description_is_cut():
    prompt = drafts.build_prompt("기획서", "제목", description="뷁" * 10000)
    assert "(이하 생략)" in prompt and prompt.count("뷁") == drafts.MAX_DESCRIPTION


def test_slugify_and_save(tmp_path):
    assert drafts.slugify('[제3회] AI: "광고"/대상?') == "제3회_AI_광고_대상"
    path = drafts.save_draft("아이디어", "[제3회] AI 공모전", "질문문 내용", "https://x", output_dir=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert path.name.endswith("_제3회_AI_공모전_아이디어.md")
    assert "질문문 내용" in text and "https://x" in text and "AI 답변" in text
