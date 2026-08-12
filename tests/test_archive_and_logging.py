import logging
import os
from pathlib import Path

import pytest

import main
from announcement_client import AnnouncementSnapshot
from banner_constants import LANGUAGES
from http_client import JsonHttpResponse
from logging_config import configure_logging


def test_banner_announcement_list_preserves_history_and_is_idempotent(tmp_path):
    path = tmp_path / "ann_archive" / "banner_ann_list.txt"
    path.parent.mkdir()
    path.write_text("12\n10\n12\n", encoding="utf-8")

    main.update_banner_announcement_list([10, 14, 14, 16], path)
    first_result = path.read_bytes()
    main.update_banner_announcement_list([10, 14, 14, 16], path)

    assert first_result.decode("utf-8") == os.linesep.join(["12", "10", "14", "16", ""])
    assert path.read_bytes() == first_result


def test_archive_uses_snapshot_without_network_and_warns_for_missing_language(
    tmp_path,
    monkeypatch,
    caplog,
):
    monkeypatch.chdir(tmp_path)
    announcement = {"ann_id": 42, "content": "zh content"}
    by_id = {
        language: ({42: {"ann_id": 42, "content": f"{language} content"}} if language != "ja" else {})
        for language in LANGUAGES
    }
    snapshot = AnnouncementSnapshot(ordered={}, by_id=by_id)

    with caplog.at_level(logging.WARNING):
        main.archive_announcement(announcement, snapshot)

    assert Path("ann_archive/42/zh-cn.txt").read_text(encoding="utf-8") == "zh content"
    assert Path("ann_archive/42/en-us.txt").read_text(encoding="utf-8") == "en-us content"
    assert not Path("ann_archive/42/ja.txt").exists()
    assert "language=ja ann_id=42" in caplog.text


def test_archive_write_errors_are_logged_and_reraised(tmp_path, monkeypatch, caplog):
    def fail_write(self, content, encoding):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", fail_write)
    path = tmp_path / "ann_archive" / "42" / "zh-cn.txt"

    with caplog.at_level(logging.ERROR):
        with pytest.raises(OSError, match="disk full"):
            main._write_archive_file(path, "content", language="zh-cn", announcement_id=42)

    assert "language=zh-cn ann_id=42" in caplog.text
    assert "disk full" in caplog.text


def test_existing_monitoring_content_is_info_and_old_debug_content_is_debug(caplog):
    snapshot = AnnouncementSnapshot(ordered={}, by_id={language: {} for language in LANGUAGES})
    announcement = {
        "ann_id": 1,
        "title": "ordinary announcement",
        "subtitle": "subtitle",
        "content": "full monitored announcement body",
    }

    with caplog.at_level(logging.INFO):
        assert main.announcement_to_banner_meta(announcement, [], snapshot=snapshot) is None
        main.convert_chinese_version("「月之一」")

    assert "full monitored announcement body" in caplog.text
    assert "Converting Chinese version" not in caplog.text

    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        main.convert_chinese_version("「月之一」")
    assert "Converting Chinese version" in caplog.text


def test_invalid_log_level_fails_explicitly():
    with pytest.raises(ValueError, match="Invalid LOG_LEVEL"):
        configure_logging("verbose")


class ItemClient:
    def __init__(self):
        self.names = []

    def post_json(self, url, *, body, context, retry):
        self.names.append(body["item_name"])
        return JsonHttpResponse(
            payload={"item_id": len(self.names)},
            status_code=200,
            text="{}",
        )


def test_item_ids_are_cached_for_the_duration_of_a_run():
    client = ItemClient()
    cache = {}

    resolved = main.resolve_item_ids(["A", "B", "A"], cache, client)

    assert resolved == [1, 2, 1]
    assert client.names == ["A", "B"]


def test_workflow_connects_log_level_and_defaults_to_info():
    workflow = (Path(__file__).parents[1] / ".github/workflows/banner-generator.yml").read_text(
        encoding="utf-8"
    )

    assert "default: 'info'" in workflow
    assert "LOG_LEVEL: ${{ inputs.logLevel }}" in workflow
