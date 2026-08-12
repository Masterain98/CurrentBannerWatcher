import pytest

import main
from banner_schedule import (
    BannerScheduleResolutionError,
    MAINTENANCE_NOTICE,
    UPDATE_DETAILS,
    resolve_relative_banner_start,
)


VERSION_MAP = {"「月之八」": "6.7"}


def announcement(
    announcement_id: int,
    subtitle: str,
    content: str,
) -> dict:
    return {
        "ann_id": announcement_id,
        "subtitle": subtitle,
        "content": content,
    }


def update_details(
    announcement_id: int,
    version: str,
    start_time: str,
) -> dict:
    return announcement(
        announcement_id,
        f"{version}版本更新说明",
        "〓更新时间〓"
        f'&lt;t class="t_gl" contenteditable="false"&gt;{start_time}&lt;/t&gt;开始',
    )


def maintenance_notice(
    announcement_id: int,
    version: str,
    start_time: str,
) -> dict:
    return announcement(
        announcement_id,
        f"{version}版本更新维护预告",
        "制作组预计将于"
        f'&lt;t class="t_gl" contenteditable="false"&gt;{start_time}&lt;/t&gt;'
        "进行版本更新维护",
    )


def resolve(announcements: list[dict]):
    return resolve_relative_banner_start(
        version_text="「月之八」",
        numeric_version="6.7",
        announcements=announcements,
        chinese_version_map=VERSION_MAP,
    )


def test_current_maintenance_notice_wins_by_exact_version_not_api_order():
    result = resolve(
        [
            update_details(21730, "「月之七」", "2026/05/20 06:00"),
            maintenance_notice(21779, "「月之八」", "2026/07/01 06:00"),
        ]
    )

    assert result.start_time == "2026/07/01 06:00"
    assert [(item.source_type, item.announcement_id) for item in result.evidence] == [
        (MAINTENANCE_NOTICE, 21779)
    ]


def test_numeric_and_chinese_sources_may_corroborate_when_they_agree():
    result = resolve(
        [
            update_details(21789, "「月之八」", "2026/07/01 06:00"),
            maintenance_notice(21779, "6.7", "2026/07/01 06:00"),
        ]
    )

    assert result.start_time == "2026/07/01 06:00"
    assert {item.source_type for item in result.evidence} == {
        UPDATE_DETAILS,
        MAINTENANCE_NOTICE,
    }


def test_duplicate_exact_sources_are_not_resolved_by_taking_the_first():
    with pytest.raises(BannerScheduleResolutionError, match="Expected a unique"):
        resolve(
            [
                update_details(1, "「月之八」", "2026/07/01 06:00"),
                update_details(2, "6.7", "2026/07/01 06:00"),
            ]
        )


def test_conflicting_exact_sources_stop_resolution():
    with pytest.raises(BannerScheduleResolutionError, match="Conflicting update start"):
        resolve(
            [
                update_details(1, "「月之八」", "2026/07/01 06:00"),
                maintenance_notice(2, "6.7", "2026/07/02 06:00"),
            ]
        )


def test_missing_or_malformed_current_version_evidence_stops_resolution():
    with pytest.raises(BannerScheduleResolutionError, match="No exact"):
        resolve([update_details(1, "「月之七」", "2026/05/20 06:00")])

    with pytest.raises(BannerScheduleResolutionError, match="Could not parse"):
        resolve([announcement(2, "「月之八」版本更新说明", "没有更新时间")])


def test_run_skips_publication_with_successful_actions_warning(
    monkeypatch,
    capsys,
    caplog,
):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(main, "RUN_MODE", "production")
    monkeypatch.setattr(main, "configure_logging", lambda: None)
    monkeypatch.setattr(main, "get_default_http_client", object)
    monkeypatch.setattr(
        main,
        "refresh_all_banner_data",
        lambda client: (_ for _ in ()).throw(
            BannerScheduleResolutionError("ambiguous schedule: two candidates")
        ),
    )
    monkeypatch.setattr(
        main,
        "create_banner",
        lambda *args, **kwargs: pytest.fail("publication must be skipped"),
    )

    main.run()

    output = capsys.readouterr().out
    assert output.startswith("::warning title=Banner publication skipped::")
    assert "ambiguous schedule: two candidates" in output
    assert "no banner publication request was sent" in output
    assert "Banner publication skipped" in caplog.text


def test_non_schedule_failures_still_fail_the_run(monkeypatch):
    monkeypatch.setattr(main, "RUN_MODE", "production")
    monkeypatch.setattr(main, "configure_logging", lambda: None)
    monkeypatch.setattr(main, "get_default_http_client", object)
    monkeypatch.setattr(
        main,
        "refresh_all_banner_data",
        lambda client: (_ for _ in ()).throw(OSError("disk full")),
    )

    with pytest.raises(OSError, match="disk full"):
        main.run()
