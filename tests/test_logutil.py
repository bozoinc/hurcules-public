"""Tests for hurcules.logutil — stdlib logging helper (pure, no network)."""
import logging

import pytest

from hurcules import logutil


@pytest.fixture
def fresh_config(monkeypatch):
    """Reset logutil's once-only guard so env re-resolution is testable.

    monkeypatch restores the original module state after each test, keeping
    the process-wide logging config side effects limited to this test file.
    """
    monkeypatch.setattr(logutil, "_configured", False)
    monkeypatch.setattr(logutil, "_level", None)
    yield


def test_get_logger_returns_named_logger():
    logger = logutil.get_logger("hurcules.mapper")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "hurcules.mapper"


def test_default_level_is_warning(fresh_config, monkeypatch):
    monkeypatch.delenv("HURCULES_LOG_LEVEL", raising=False)
    logger = logutil.get_logger("hurcules.test")
    assert logger.level == logging.WARNING


@pytest.mark.parametrize("env,expected", [
    ("DEBUG", logging.DEBUG),
    ("INFO", logging.INFO),
    ("WARNING", logging.WARNING),
    ("ERROR", logging.ERROR),
])
def test_env_level_honored(fresh_config, monkeypatch, env, expected):
    monkeypatch.setenv("HURCULES_LOG_LEVEL", env)
    assert logutil.get_logger("hurcules.test").level == expected


def test_invalid_env_level_falls_back_to_warning(fresh_config, monkeypatch):
    monkeypatch.setenv("HURCULES_LOG_LEVEL", "VERBOSE")
    assert logutil.get_logger("hurcules.test").level == logging.WARNING


def test_logged_call_does_not_crash(fresh_config, monkeypatch, caplog):
    monkeypatch.setenv("HURCULES_LOG_LEVEL", "DEBUG")
    logger = logutil.get_logger("hurcules.test")
    with caplog.at_level(logging.DEBUG, logger="hurcules.test"):
        logger.info("map start repo_dir=%s", "/tmp/x")
        logger.warning("boom %s", 42)
    assert [r.name for r in caplog.records] == ["hurcules.test", "hurcules.test"]
    assert caplog.records[0].message == "map start repo_dir=/tmp/x"