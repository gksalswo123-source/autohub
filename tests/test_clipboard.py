"""클립보드에서 토큰 읽기 테스트 (진짜 클립보드는 건드리지 않음)."""

import subprocess

from autohub import cli


def fake_clipboard(monkeypatch, text):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout=text, stderr="")
    monkeypatch.setattr(cli.subprocess, "run", run)


def test_reads_token_with_whitespace(monkeypatch):
    fake_clipboard(monkeypatch, "  " + "a1" * 20 + "\r\n")
    assert cli.read_clipboard_token() == "a1" * 20


def test_ignores_non_token(monkeypatch):
    fake_clipboard(monkeypatch, "그냥 복사한 글자")
    assert cli.read_clipboard_token() is None
