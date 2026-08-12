from dataclasses import dataclass
from typing import Any

from banner_constants import LANGUAGES
from http_client import HttpClient


ANNOUNCEMENT_URL = (
    "https://sg-hk4e-api-static.hoyoverse.com/common/hk4e_global/announcement/api/getAnnContent"
)


@dataclass(frozen=True)
class AnnouncementSnapshot:
    ordered: dict[str, list[dict[str, Any]]]
    by_id: dict[str, dict[int, dict[str, Any]]]


def announcement_params(language: str) -> dict[str, str]:
    return {
        "game": "hk4e",
        "game_biz": "hk4e_global",
        "region": "os_asia",
        "bundle_id": "hk4e_global",
        "channel_id": "1",
        "level": "55",
        "platform": "pc",
        "lang": language,
        "uid": "100000000",
    }


def fetch_announcement_snapshot(client: HttpClient) -> AnnouncementSnapshot:
    ordered: dict[str, list[dict[str, Any]]] = {}
    by_id: dict[str, dict[int, dict[str, Any]]] = {}

    for language in LANGUAGES:
        response = client.get_json(
            ANNOUNCEMENT_URL,
            params=announcement_params(language),
            context=f"Failed to fetch announcement list for language={language}",
        )
        retcode = response.payload.get("retcode")
        message = response.payload.get("message")
        status_context = f"retcode={retcode!r} message={message!r}"
        if retcode not in (None, 0):
            raise ValueError(
                f"Announcement API failed for language={language} ({status_context})"
            )
        data = response.payload.get("data")
        if not isinstance(data, dict):
            raise ValueError(
                f"Announcement response for language={language} has no object data field "
                f"({status_context})"
            )
        announcements = data.get("list")
        if not isinstance(announcements, list):
            raise ValueError(
                f"Announcement response for language={language} has no list field "
                f"({status_context})"
            )

        language_index: dict[int, dict[str, Any]] = {}
        for position, announcement in enumerate(announcements):
            if not isinstance(announcement, dict):
                raise ValueError(
                    f"Announcement language={language} index={position} is not an object"
                )
            announcement_id = announcement.get("ann_id")
            if not isinstance(announcement_id, int):
                raise ValueError(
                    f"Announcement language={language} index={position} has invalid ann_id"
                )
            if announcement_id in language_index:
                raise ValueError(
                    f"Announcement language={language} contains duplicate ann_id={announcement_id}"
                )
            language_index[announcement_id] = announcement

        ordered[language] = announcements
        by_id[language] = language_index

    return AnnouncementSnapshot(ordered=ordered, by_id=by_id)
