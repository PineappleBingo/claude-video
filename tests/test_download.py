"""yt-dlp argv construction for download.py.

Regression guard: ``--sub-langs all`` makes yt-dlp fetch YouTube's hundreds of
auto-translated caption tracks, which can take minutes and stalls before the
video download even starts. The request stays bounded: English-only by
default, and any configured list (``WATCH_SUB_LANGS``) is passed through
verbatim — except ``all``, which is rejected back to the default.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "watch" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import config  # noqa: E402
import download  # noqa: E402

URL = "https://www.youtube.com/watch?v=rlOpbu3Enkw"


def _capture_argv(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Stub subprocess.run inside download.py and record every argv."""
    calls: list[list[str]] = []

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        return _Result()

    monkeypatch.setattr(download.subprocess, "run", fake_run)
    # The argv is what we test; the binary itself is not needed (CI runners
    # without yt-dlp must not fail these tests).
    monkeypatch.setattr(download.shutil, "which", lambda name: f"/usr/bin/{name}")
    return calls


def _isolate_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "missing.env")
    monkeypatch.delenv("WATCH_SUB_LANGS", raising=False)


def _sub_langs(argv: list[str]) -> str:
    idx = argv.index("--sub-langs")
    return argv[idx + 1]


def _assert_bounded(langs: str) -> None:
    tokens = langs.split(",")
    assert "all" not in tokens, f"sub-langs must not request all languages, got {langs!r}"


def test_fetch_captions_requests_english_only_by_default(monkeypatch, tmp_path):
    _isolate_config(monkeypatch, tmp_path)
    calls = _capture_argv(monkeypatch)
    download.fetch_captions(URL, tmp_path / "download")
    langs = _sub_langs(calls[0])
    _assert_bounded(langs)
    assert all(t.startswith("en") for t in langs.split(",")), f"default must be English-only, got {langs!r}"


def test_download_url_requests_english_only_by_default(monkeypatch, tmp_path):
    _isolate_config(monkeypatch, tmp_path)
    calls = _capture_argv(monkeypatch)
    # _pick_video returns None with no real file, which raises SystemExit after
    # the yt-dlp argv is already built — that's all we need to inspect.
    with pytest.raises(SystemExit):
        download.download_url(URL, tmp_path / "download")
    langs = _sub_langs(calls[0])
    _assert_bounded(langs)
    assert all(t.startswith("en") for t in langs.split(","))


def test_env_sub_langs_are_passed_through(monkeypatch, tmp_path):
    _isolate_config(monkeypatch, tmp_path)
    monkeypatch.setenv("WATCH_SUB_LANGS", "ko.*,en.*")
    calls = _capture_argv(monkeypatch)
    download.fetch_captions(URL, tmp_path / "download")
    assert _sub_langs(calls[0]) == "ko.*,en.*"


def test_explicit_sub_langs_argument_wins(monkeypatch, tmp_path):
    _isolate_config(monkeypatch, tmp_path)
    monkeypatch.setenv("WATCH_SUB_LANGS", "ko.*,en.*")
    calls = _capture_argv(monkeypatch)
    download.fetch_captions(URL, tmp_path / "download", sub_langs="ja.*")
    assert _sub_langs(calls[0]) == "ja.*"


def test_all_is_rejected_back_to_default(monkeypatch, tmp_path):
    _isolate_config(monkeypatch, tmp_path)
    monkeypatch.setenv("WATCH_SUB_LANGS", "all")
    calls = _capture_argv(monkeypatch)
    download.fetch_captions(URL, tmp_path / "download")
    langs = _sub_langs(calls[0])
    _assert_bounded(langs)
    assert langs == config.DEFAULT_SUB_LANGS


def test_pick_subtitle_prefers_configured_language_order(tmp_path):
    out = tmp_path / "download"
    out.mkdir()
    (out / "video.en.vtt").write_text("WEBVTT\n")
    (out / "video.ko.vtt").write_text("WEBVTT\n")
    (out / "video.ja.vtt").write_text("WEBVTT\n")
    assert download._pick_subtitle(out, "ko.*,en.*").name == "video.ko.vtt"
    assert download._pick_subtitle(out, "en.*").name == "video.en.vtt"
    # Nothing configured matches → any track beats no track.
    assert download._pick_subtitle(out, "fr.*") is not None


def test_pick_subtitle_matches_region_variants(tmp_path):
    out = tmp_path / "download"
    out.mkdir()
    (out / "video.ko-KR.vtt").write_text("WEBVTT\n")
    (out / "video.en-orig.vtt").write_text("WEBVTT\n")
    assert download._pick_subtitle(out, "ko.*,en.*").name == "video.ko-KR.vtt"
    assert download._pick_subtitle(out, "en.*").name == "video.en-orig.vtt"
