from pathlib import Path

import pytest
import requests

from announcement_client import fetch_announcement_snapshot
from banner_constants import LANGUAGES
from banner_downloader import cache_image_urls, image_destination
from http_client import (
    HttpClient,
    HttpClientError,
    JsonHttpResponse,
    build_read_retry,
)


class FakeResponse:
    def __init__(
        self,
        payload=None,
        *,
        status_code=200,
        text="{}",
        error: Exception | None = None,
        chunks=(),
    ):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.text = text
        self._error = error
        self._chunks = chunks

    def raise_for_status(self):
        if self._error:
            raise self._error

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def iter_content(self, chunk_size):
        assert chunk_size == 64 * 1024
        for chunk in self._chunks:
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class RecordingSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)


def test_read_retry_is_three_total_attempts_and_handles_transient_statuses():
    retry = build_read_retry()

    assert retry.total == 2
    assert retry.backoff_factor == 0.5
    assert retry.status_forcelist == (429, 500, 502, 503, 504)
    assert retry.allowed_methods == frozenset({"GET", "POST"})
    assert retry.respect_retry_after_header is True


def test_read_and_write_posts_use_separate_sessions_without_publish_retry():
    read_session = RecordingSession([FakeResponse({"item_id": 1})])
    write_session = RecordingSession([FakeResponse({"message": "ok"})])
    client = HttpClient(read_session=read_session, write_session=write_session)

    client.post_json("https://read.test", body={}, context="read", retry=True)
    client.post_json("https://write.test", body={}, context="write", retry=False)

    assert [call[1] for call in read_session.calls] == ["https://read.test"]
    assert [call[1] for call in write_session.calls] == ["https://write.test"]
    assert read_session.calls[0][2]["timeout"] == (5, 30)
    assert write_session.calls[0][2]["timeout"] == (5, 30)


def test_default_write_session_has_no_retries():
    client = HttpClient()

    read_adapter = client.read_session.get_adapter("https://example.test")
    write_adapter = client.write_session.get_adapter("https://example.test")

    assert read_adapter.max_retries.total == 2
    assert write_adapter.max_retries.total == 0


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(error=requests.HTTPError("bad status")),
        FakeResponse(ValueError("invalid json")),
        FakeResponse(["not", "an", "object"]),
    ],
)
def test_json_failures_include_request_context(response):
    client = HttpClient(
        read_session=RecordingSession([response]),
        write_session=RecordingSession([]),
    )

    with pytest.raises(HttpClientError, match="announcement language=ja"):
        client.get_json("https://example.test", context="announcement language=ja")


def test_download_uses_image_timeout_and_deduplicates_urls(tmp_path, monkeypatch):
    session = RecordingSession([FakeResponse(chunks=[b"abc", b"", b"def"])])
    client = HttpClient(read_session=session, write_session=RecordingSession([]))
    monkeypatch.chdir(tmp_path)

    cache_image_urls(
        [
            "https://sdk.hoyoverse.com/upload/banner.jpg",
            "https://sdk.hoyoverse.com/upload/banner.jpg",
        ],
        client,
    )

    assert len(session.calls) == 1
    assert session.calls[0][2] == {"timeout": (5, 60), "stream": True}
    assert Path("upload/banner.jpg").read_bytes() == b"abcdef"


def test_image_destination_rejects_foreign_hosts_and_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="Unsupported banner image URL"):
        image_destination("https://example.test/upload/banner.jpg")
    with pytest.raises(ValueError, match="escapes the working directory"):
        image_destination("https://sdk.hoyoverse.com/../outside.jpg")


def test_failed_download_preserves_existing_file_and_removes_temporary_file(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    destination = Path("upload/banner.jpg")
    destination.parent.mkdir()
    destination.write_bytes(b"existing")
    response = FakeResponse(chunks=[b"replacement", requests.ConnectionError("stream failed")])
    client = HttpClient(
        read_session=RecordingSession([response]),
        write_session=RecordingSession([]),
    )

    with pytest.raises(HttpClientError, match="stream failed"):
        client.download_file(
            "https://sdk.hoyoverse.com/upload/banner.jpg",
            destination,
            context="failed image",
        )

    assert destination.read_bytes() == b"existing"
    assert list(destination.parent.glob(".banner-download-*")) == []


class SnapshotClient:
    def __init__(self):
        self.languages = []

    def get_json(self, url, *, params, context):
        language = params["lang"]
        self.languages.append(language)
        announcement = {
            "ann_id": 42,
            "title": "title",
            "subtitle": f"subtitle-{language}",
            "content": f"content-{language}",
        }
        return JsonHttpResponse(
            payload={"data": {"list": [announcement]}},
            status_code=200,
            text="{}",
        )


def test_announcement_snapshot_fetches_each_language_once_and_indexes_by_id():
    client = SnapshotClient()

    snapshot = fetch_announcement_snapshot(client)

    assert client.languages == list(LANGUAGES)
    assert len(client.languages) == 15
    assert snapshot.by_id["ja"][42]["content"] == "content-ja"
    assert snapshot.ordered["zh-cn"][0]["ann_id"] == 42


class FailedSnapshotClient:
    def get_json(self, url, *, params, context):
        return JsonHttpResponse(
            payload={"retcode": -1, "message": "maintenance", "data": {"list": []}},
            status_code=200,
            text="{}",
        )


def test_announcement_api_errors_include_retcode_message_and_language():
    with pytest.raises(
        ValueError,
        match=r"language=zh-cn.*retcode=-1.*message='maintenance'",
    ):
        fetch_announcement_snapshot(FailedSnapshotClient())
