"""When Google refuses the model call, the visitor still gets the fallback, and the log says why."""
import logging

import httpx
import pytest

from app.rag import llm


def fake_google(monkeypatch, status, body):
    real = httpx.AsyncClient
    monkeypatch.setenv("GEMINI_API_KEY", "secret-key-123")
    monkeypatch.setattr(
        llm.httpx,
        "AsyncClient",
        lambda **kwargs: real(transport=httpx.MockTransport(lambda request: httpx.Response(status, json=body)), **kwargs),
    )


async def test_a_retired_model_is_logged_with_the_reason_and_never_the_key(monkeypatch, caplog):
    fake_google(monkeypatch, 404, {"error": {"message": "This model models/x is no longer available to new users."}})
    with caplog.at_level(logging.WARNING, logger="portfolio.llm"), pytest.raises(llm.LLMUnavailable):
        await llm.Gemini().generate("system", "user", llm.CHEAP)
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "404" in text and "no longer available" in text and "gemini-3.5-flash-lite" in text
    assert "secret-key-123" not in text


async def test_a_good_reply_logs_nothing(monkeypatch, caplog):
    fake_google(monkeypatch, 200, {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]})
    with caplog.at_level(logging.WARNING, logger="portfolio.llm"):
        assert await llm.Gemini().generate("system", "user", llm.SMART) == "hello"
    assert not caplog.records


async def test_an_error_body_that_is_not_json_does_not_hide_the_failure(monkeypatch, caplog):
    real = httpx.AsyncClient
    monkeypatch.setattr(
        llm.httpx,
        "AsyncClient",
        lambda **kwargs: real(transport=httpx.MockTransport(lambda request: httpx.Response(502, text="<html>bad gateway</html>")), **kwargs),
    )
    with caplog.at_level(logging.WARNING, logger="portfolio.llm"), pytest.raises(llm.LLMUnavailable):
        await llm.Gemini().generate("system", "user", llm.CHEAP)
    assert any("502" in r.getMessage() for r in caplog.records)
