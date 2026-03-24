"""Tests for single-instance process guard."""

from __future__ import annotations

import os

import pytest

from mycelium.shared.process_guard import ProcessGuard


def test_acquire_creates_pid_file(tmp_path):
    pid_file = tmp_path / "mycelium.pid"
    guard = ProcessGuard(pid_file)
    guard.acquire()

    assert pid_file.exists()
    assert int(pid_file.read_text().strip()) == os.getpid()

    guard.release()


def test_release_removes_pid_file(tmp_path):
    pid_file = tmp_path / "mycelium.pid"
    guard = ProcessGuard(pid_file)
    guard.acquire()
    guard.release()

    assert not pid_file.exists()


def test_stale_pid_is_cleaned(tmp_path):
    pid_file = tmp_path / "mycelium.pid"
    pid_file.write_text("999999999")

    guard = ProcessGuard(pid_file)
    guard.acquire()

    assert pid_file.exists()
    assert int(pid_file.read_text().strip()) == os.getpid()

    guard.release()


def test_active_pid_raises(tmp_path):
    pid_file = tmp_path / "mycelium.pid"
    pid_file.write_text(str(os.getpid()))

    guard = ProcessGuard(pid_file)
    with pytest.raises(RuntimeError, match="already running"):
        guard.acquire()
