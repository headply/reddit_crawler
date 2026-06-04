"""Tests for LLMCircuitBreaker."""

import threading

import pytest

from src.nlp.circuit_breaker import LLMCircuitBreaker


def test_starts_closed():
    cb = LLMCircuitBreaker(threshold=3)
    assert cb.is_tripped() is False


def test_trips_after_threshold_consecutive_failures():
    cb = LLMCircuitBreaker(threshold=3)
    for _ in range(2):
        cb.record_failure(RuntimeError("boom"))
        assert cb.is_tripped() is False
    cb.record_failure(RuntimeError("boom"))
    assert cb.is_tripped() is True


def test_success_resets_consecutive_counter():
    cb = LLMCircuitBreaker(threshold=3)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    cb.record_failure()
    # Only two failures since last success.
    assert cb.is_tripped() is False


def test_force_trip_is_immediate_and_idempotent():
    cb = LLMCircuitBreaker(threshold=5)
    cb.force_trip("key missing")
    cb.force_trip("again")
    assert cb.is_tripped() is True


def test_counters_track_totals():
    cb = LLMCircuitBreaker(threshold=10)
    for _ in range(4):
        cb.record_failure()
    cb.record_success()
    assert cb.total_failures == 4
    assert cb.total_successes == 1


def test_status_message_changes_when_tripped():
    cb = LLMCircuitBreaker(threshold=1)
    assert "OK" in cb.status_message()
    cb.record_failure()
    assert "TRIPPED" in cb.status_message()


def test_thread_safe_under_contention():
    cb = LLMCircuitBreaker(threshold=200)

    def hammer():
        for _ in range(100):
            cb.record_failure()

    threads = [threading.Thread(target=hammer) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert cb.total_failures == 1000
    assert cb.is_tripped() is True


def test_threshold_must_be_positive():
    with pytest.raises(ValueError):
        LLMCircuitBreaker(threshold=0)
