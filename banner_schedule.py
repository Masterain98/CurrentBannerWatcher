import html
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from bs4 import BeautifulSoup


UPDATE_DETAILS = "update-details"
MAINTENANCE_NOTICE = "maintenance-notice"

_SOURCE_SUFFIXES = {
    UPDATE_DETAILS: "版本更新说明",
    MAINTENANCE_NOTICE: "版本更新维护预告",
}

_TIME_PATTERNS = {
    UPDATE_DETAILS: re.compile(
        r"〓更新时间〓\s*(?P<start>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}(?::\d{2})?)\s*开始"
    ),
    MAINTENANCE_NOTICE: re.compile(
        r"预计将于\s*(?P<start>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}(?::\d{2})?)"
        r"\s*进行版本更新维护"
    ),
}


class BannerScheduleResolutionError(RuntimeError):
    """Raised when a banner schedule cannot be resolved without guessing."""


@dataclass(frozen=True)
class ScheduleEvidence:
    announcement_id: int
    subtitle: str
    source_type: str
    start_time: str


@dataclass(frozen=True)
class ScheduleResolution:
    start_time: str
    evidence: tuple[ScheduleEvidence, ...]


def _plain_announcement_text(content: str) -> str:
    # Announcement timestamps are commonly encoded as literal ``<t>`` elements.
    # Unescaping before parsing makes the timestamp available as ordinary text.
    return BeautifulSoup(html.unescape(content), "html.parser").get_text(
        "", strip=True
    )


def _version_aliases(
    version_text: str,
    numeric_version: str,
    chinese_version_map: Mapping[str, str],
) -> set[str]:
    aliases = {version_text, numeric_version}
    aliases.update(
        chinese_version
        for chinese_version, mapped_version in chinese_version_map.items()
        if mapped_version == numeric_version
    )
    return aliases


def _matching_announcements(
    announcements: Sequence[dict[str, Any]],
    expected_subtitles: set[str],
) -> list[dict[str, Any]]:
    return [
        announcement
        for announcement in announcements
        if announcement.get("subtitle") in expected_subtitles
    ]


def _extract_evidence(
    announcement: dict[str, Any],
    source_type: str,
) -> ScheduleEvidence:
    announcement_id = announcement.get("ann_id")
    subtitle = announcement.get("subtitle")
    content = announcement.get("content")
    if not isinstance(announcement_id, int):
        raise BannerScheduleResolutionError(
            f"Matched {source_type} announcement has invalid ann_id={announcement_id!r}"
        )
    if not isinstance(subtitle, str) or not isinstance(content, str):
        raise BannerScheduleResolutionError(
            f"Matched {source_type} announcement ann_id={announcement_id} has invalid fields"
        )

    match = _TIME_PATTERNS[source_type].search(_plain_announcement_text(content))
    if match is None:
        raise BannerScheduleResolutionError(
            f"Could not parse update start time from {source_type} "
            f"ann_id={announcement_id} subtitle={subtitle!r}"
        )
    return ScheduleEvidence(
        announcement_id=announcement_id,
        subtitle=subtitle,
        source_type=source_type,
        start_time=match.group("start"),
    )


def resolve_relative_banner_start(
    *,
    version_text: str,
    numeric_version: str,
    announcements: Sequence[dict[str, Any]],
    chinese_version_map: Mapping[str, str],
) -> ScheduleResolution:
    """Resolve a ``版本更新后`` start using exact, version-specific evidence.

    One update-details announcement and one maintenance notice may coexist. They
    are accepted only when both independently produce the same timestamp.
    Multiple matches of either source type, conflicting timestamps, malformed
    evidence, or a complete lack of evidence are all treated as unresolved.
    """

    aliases = _version_aliases(
        version_text,
        numeric_version,
        chinese_version_map,
    )
    evidence: list[ScheduleEvidence] = []

    for source_type, suffix in _SOURCE_SUFFIXES.items():
        expected_subtitles = {f"{alias}{suffix}" for alias in aliases}
        matches = _matching_announcements(announcements, expected_subtitles)
        if len(matches) > 1:
            matched = ", ".join(
                f"ann_id={item.get('ann_id')} subtitle={item.get('subtitle')!r}"
                for item in matches
            )
            raise BannerScheduleResolutionError(
                f"Expected a unique {source_type} announcement for "
                f"version={numeric_version}, found {len(matches)}: {matched}"
            )
        if matches:
            evidence.append(_extract_evidence(matches[0], source_type))

    if not evidence:
        expected = ", ".join(
            sorted(
                f"{alias}{suffix}"
                for alias in aliases
                for suffix in _SOURCE_SUFFIXES.values()
            )
        )
        raise BannerScheduleResolutionError(
            f"No exact update schedule announcement found for version={numeric_version}; "
            f"expected one of: {expected}"
        )

    times = {item.start_time for item in evidence}
    if len(times) != 1:
        details = ", ".join(
            f"{item.source_type} ann_id={item.announcement_id} time={item.start_time}"
            for item in evidence
        )
        raise BannerScheduleResolutionError(
            f"Conflicting update start times for version={numeric_version}: {details}"
        )

    return ScheduleResolution(
        start_time=evidence[0].start_time,
        evidence=tuple(evidence),
    )
