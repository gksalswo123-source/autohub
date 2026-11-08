"""토큰 저장/읽기 테스트."""

import os

from autohub.config import load_env, save_secret


def test_save_then_load(tmp_path, monkeypatch):
    monkeypatch.delenv("DEMO_TOKEN", raising=False)
    env = tmp_path / ".env"
    save_secret("DEMO_TOKEN", "old", path=env)
    save_secret("DEMO_TOKEN", "  new  ", path=env)  # 같은 이름은 바꿔 씀
    assert env.read_text(encoding="utf-8").count("DEMO_TOKEN=") == 1

    monkeypatch.delenv("DEMO_TOKEN")
    load_env((env,))
    assert os.environ["DEMO_TOKEN"] == "new"


def test_empty_value_in_first_file_does_not_hide_second(tmp_path, monkeypatch):
    monkeypatch.delenv("DEMO_TOKEN", raising=False)
    local, home = tmp_path / "local.env", tmp_path / "home.env"
    local.write_text("DEMO_TOKEN=\n", encoding="utf-8")  # .env.example 을 그대로 복사한 경우
    home.write_text("DEMO_TOKEN=real\n", encoding="utf-8")
    load_env((local, home))
    assert os.environ["DEMO_TOKEN"] == "real"
