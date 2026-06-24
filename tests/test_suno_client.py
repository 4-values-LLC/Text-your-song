"""Tests für SunoRequest-Validierung & Client (gegen gemockten HTTP)."""

from __future__ import annotations

import httpx
import pytest

from txtsong.models.suno import SunoRequest
from txtsong.suno.client import SunoClient, SunoValidationError, validate_request


def _valid_request(**overrides) -> SunoRequest:
    base = dict(
        upload_url="https://host/audio.wav",
        style="edm, 128 BPM, energetic",
        title="Test (Remix)",
        prompt="[Verse]\nhello\n\n[Chorus]\nworld",
        model="V4_5PLUS",
    )
    base.update(overrides)
    return SunoRequest(**base)


def test_validate_ok():
    validate_request(_valid_request())  # darf nicht werfen


def test_validate_unknown_model():
    with pytest.raises(SunoValidationError):
        validate_request(_valid_request(model="V9_NOPE"))


def test_validate_style_too_long():
    with pytest.raises(SunoValidationError):
        validate_request(_valid_request(style="x" * 1001))


def test_validate_missing_prompt_when_vocal():
    with pytest.raises(SunoValidationError):
        validate_request(_valid_request(prompt=""))


def test_payload_camel_case():
    payload = _valid_request(audio_weight=0.7, vocal_gender="f").to_api_payload()
    assert payload["uploadUrl"] == "https://host/audio.wav"
    assert payload["customMode"] is True
    assert payload["audioWeight"] == 0.7
    assert payload["vocalGender"] == "f"
    assert "callBackUrl" in payload


def test_submit_cover_parses_task_id(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        body = httpx.Response  # noqa: F841 - nur zur Klarheit
        return httpx.Response(200, json={"code": 200, "msg": "ok", "data": {"taskId": "abc123"}})

    transport = httpx.MockTransport(handler)

    # httpx.post durch eine Client-Variante mit MockTransport ersetzen.
    def fake_post(url, **kwargs):
        with httpx.Client(transport=transport) as client:
            return client.post(url, **kwargs)

    monkeypatch.setattr("txtsong.suno.client.httpx.post", fake_post)

    client = SunoClient(api_key="test-key", base_url="https://api.test")
    task_id = client.submit_cover(_valid_request())
    assert task_id == "abc123"


def test_get_result_parses_tracks(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 200,
                "data": {
                    "taskId": "abc123",
                    "status": "SUCCESS",
                    "response": {
                        "sunoData": [
                            {"id": "1", "audioUrl": "https://cdn/a.mp3", "title": "A", "duration": 180.0}
                        ]
                    },
                },
            },
        )

    transport = httpx.MockTransport(handler)

    def fake_get(url, **kwargs):
        with httpx.Client(transport=transport) as client:
            return client.get(url, **kwargs)

    monkeypatch.setattr("txtsong.suno.client.httpx.get", fake_get)

    client = SunoClient(api_key="test-key", base_url="https://api.test")
    result = client.get_result("abc123")
    assert result.status == "complete"
    assert result.tracks[0].audio_url == "https://cdn/a.mp3"
