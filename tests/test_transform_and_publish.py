import json
import logging
from pathlib import Path

import pytest

import push
from banner_constants import LANGUAGES
from banner_publisher import publish_banner_data
from banner_transform import transform_banner_data
from http_client import HttpClientError, JsonHttpResponse


REPOSITORY_ROOT = Path(__file__).parents[1]


def test_transform_matches_current_post_data_contract():
    banner_data = json.loads((REPOSITORY_ROOT / "banner-data.json").read_text(encoding="utf-8"))
    expected_text = (REPOSITORY_ROOT / "post-data.json").read_text(encoding="utf-8")
    transformed = transform_banner_data(banner_data)

    assert transformed == json.loads(expected_text)
    assert json.dumps(transformed, indent=2, ensure_ascii=False) == expected_text


def test_transform_uses_explicit_languages_and_ignores_short_metadata_key():
    language_data = {
        language: {"banner_name": f"name-{language}", "banner_image": "https://sdk.hoyoverse.com/x.jpg"}
        for language in LANGUAGES
    }
    banner = {
        "UpOrangeList": [1],
        "UpPurpleList": [2, 3, 4],
        "UIGF_pool_type": 301,
        "start_time": "2026/01/01 00:00",
        "end_time": "2026/01/21 00:00",
        "version_number": "1.0",
        "order_number": 1,
        "x": {"banner_name": "not-a-language", "banner_image": "ignored"},
        **language_data,
    }

    transformed = transform_banner_data({"1": banner})

    assert list(transformed) == list(LANGUAGES)
    assert "x" not in transformed
    assert transformed["zh-cn"][0][0]["Name"] == "name-zh-cn"
    assert transformed["zh-cn"][0][0]["From"] == "2026-01-01T00:00"
    assert isinstance(transformed["zh-cn"][0], list)


class PublishingClient:
    def __init__(self, outcomes=None):
        self.calls = []
        self.outcomes = list(outcomes or [])

    def post_json(self, url, *, body, context, retry):
        self.calls.append((url, body, context, retry))
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return JsonHttpResponse(
            payload={"message": "ok"},
            status_code=200,
            text='{"message":"ok"}',
        )


def test_publisher_preserves_nested_body_and_disables_retry():
    client = PublishingClient()
    body = [[{"Name": "Banner"}]]

    publish_banner_data(
        {"zh-cn": body},
        "https://publish.test/{locale}",
        client,
    )

    assert client.calls == [
        (
            "https://publish.test/CHS",
            body[0],
            "Failed to publish banner language=zh-cn locale=CHS",
            False,
        )
    ]


def test_missing_publish_message_warns_without_failing(caplog):
    client = PublishingClient(
        [JsonHttpResponse(payload={}, status_code=200, text="{}")]
    )

    with caplog.at_level(logging.INFO):
        publish_banner_data(
            {"zh-cn": [[{"Name": "Banner"}]]},
            "https://publish.test/{locale}",
            client,
        )

    assert "has no message field" in caplog.text


def test_publish_failure_does_not_block_remaining_locales_and_is_reraised(caplog):
    client = PublishingClient(
        [
            HttpClientError("first locale failed"),
            JsonHttpResponse(payload={"message": "ok"}, status_code=200, text="{}"),
        ]
    )
    post_data = {
        "zh-cn": [[{"Name": "Chinese"}]],
        "en-us": [[{"Name": "English"}]],
    }

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ExceptionGroup) as raised:
            publish_banner_data(post_data, "https://secret.test/{locale}", client)

    assert len(client.calls) == 2
    assert raised.value.exceptions[0].args == ("first locale failed",)
    assert "language=zh-cn locale=CHS" in caplog.text


def test_resolved_publish_endpoint_is_not_logged_at_info(caplog):
    client = PublishingClient()

    with caplog.at_level(logging.INFO):
        publish_banner_data(
            {"zh-cn": [[{"Name": "Banner"}]]},
            "https://secret.test/token/{locale}",
            client,
        )

    assert "https://secret.test" not in caplog.text
    assert "Publishing locale: CHS" in caplog.text


def test_update_banner_is_retained_and_marked_deprecated(monkeypatch):
    monkeypatch.delenv("POST_ENDPOINT", raising=False)

    with pytest.warns(DeprecationWarning, match="deprecated"):
        with pytest.raises(AttributeError, match="POST_ENDPOINT"):
            push.update_banner(client=object())


def test_create_banner_rejects_unknown_modes_before_side_effects():
    with pytest.raises(ValueError, match="Invalid run mode 'staging'"):
        push.create_banner("staging", client=object())


def test_direct_push_run_defaults_to_production(monkeypatch):
    calls = []
    monkeypatch.delenv("run_mode", raising=False)
    monkeypatch.setattr(push, "configure_logging", lambda: None)
    monkeypatch.setattr(push, "create_banner", calls.append)

    push.run()

    assert calls == ["production"]


def test_transform_missing_metadata_includes_announcement_id():
    with pytest.raises(
        ValueError,
        match=r"ann_id=42.*UpOrangeList",
    ):
        transform_banner_data({"42": {}})
