"""WATCH_DETAIL resolution and frame_cap mapping."""
from __future__ import annotations

import config


def test_default_detail_is_balanced(monkeypatch, tmp_path):
    monkeypatch.delenv("WATCH_DETAIL", raising=False)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "missing.env")
    assert config.get_config()["detail"] == "balanced"


def test_env_overrides_detail(monkeypatch, tmp_path):
    monkeypatch.setenv("WATCH_DETAIL", "efficient")
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "missing.env")
    assert config.get_config()["detail"] == "efficient"


def test_invalid_detail_falls_back_to_default(monkeypatch, tmp_path):
    monkeypatch.setenv("WATCH_DETAIL", "bogus")
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "missing.env")
    assert config.get_config()["detail"] == "balanced"


def test_get_config_keys(monkeypatch, tmp_path):
    monkeypatch.delenv("WATCH_DETAIL", raising=False)
    monkeypatch.delenv("WATCH_SUB_LANGS", raising=False)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "missing.env")
    cfg = config.get_config()
    assert set(cfg) == {"detail", "sub_langs", "config_file"}
    assert cfg["sub_langs"] == config.DEFAULT_SUB_LANGS


def test_sub_langs_from_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("WATCH_SUB_LANGS", raising=False)
    env = tmp_path / ".env"
    env.write_text("WATCH_SUB_LANGS=ko.*,en.*\n")
    monkeypatch.setattr(config, "CONFIG_FILE", env)
    assert config.get_config()["sub_langs"] == "ko.*,en.*"


def test_normalize_sub_langs():
    assert config.normalize_sub_langs(None) == "en.*"
    assert config.normalize_sub_langs("") == "en.*"
    assert config.normalize_sub_langs(" ko.* , en.* ") == "ko.*,en.*"
    assert config.normalize_sub_langs("all") == "en.*"
    assert config.normalize_sub_langs("ko.*,all") == "en.*"
    assert config.normalize_sub_langs("ko;rm -rf") == "en.*"


def test_frame_cap_mapping():
    assert config.frame_cap("efficient") == 50
    assert config.frame_cap("balanced") == 100
    assert config.frame_cap("token-burner") is None
    assert config.frame_cap("transcript") is None
    assert config.frame_cap("anything-else") == 100
