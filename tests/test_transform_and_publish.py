import json
from pathlib import Path

import pytest

import push
from banner_constants import LANGUAGES
from banner_publisher import publish_banner_data
from banner_transform import transform_banner_data
from http_client import JsonHttpResponse


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
    def __init__(self):
        self.calls = []

    def post_json(self, url, *, body, context, retry):
        self.calls.append((url, body, context, retry))
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


def test_update_banner_is_retained_and_marked_deprecated(monkeypatch):
    monkeypatch.delenv("POST_ENDPOINT", raising=False)

    with pytest.warns(DeprecationWarning, match="deprecated"):
        with pytest.raises(AttributeError, match="POST_ENDPOINT"):
            push.update_banner()
