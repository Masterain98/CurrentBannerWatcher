import os
import re
import json
import logging
import sys
from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from announcement_client import (
    ANNOUNCEMENT_URL,
    AnnouncementSnapshot,
    announcement_params,
    fetch_announcement_snapshot,
)
from banner_constants import TARGET_LANGUAGES
from push import create_banner, validate_run_mode
from BannerMeta import BannerMeta
from colorama import Fore, Back, Style
from http_client import HttpClient, get_default_http_client
from logging_config import configure_logging


logger = logging.getLogger(__name__)

RUN_MODE = os.getenv("run_mode", "production")

CHINESE_VERSION_MAP = {
    "「月之一」": "6.0",
    "「月之二」": "6.1",
    "「月之三」": "6.2",
    "「月之四」": "6.3",
    "「月之五」": "6.4",
    "「月之六」": "6.5",
    "「月之七」": "6.6",
    "「月之八」": "6.7",
    "「月之九」": "6.8"
}
# Global counter for announcement separator
ANNOUNCEMENT_COUNT = 1

def print_separator():
    global ANNOUNCEMENT_COUNT
    separator = f"\n{Fore.WHITE}{Back.BLACK}╔══════════════════ Announcement {ANNOUNCEMENT_COUNT} ══════════════════╗{Style.RESET_ALL}"
    logger.info("%s", separator)
    ANNOUNCEMENT_COUNT += 1

def convert_chinese_version(version_text):
    """Convert Chinese version format to numeric version"""
    logger.debug("%s[Conversion] Converting Chinese version: %s", Fore.LIGHTYELLOW_EX, version_text)
    for chinese_ver, numeric_ver in CHINESE_VERSION_MAP.items():
        if chinese_ver in version_text:
            return numeric_ver
    return version_text  # Return original if no match found


def get_item_id_by_name(name: str, client: HttpClient | None = None) -> int:
    http_client = client or get_default_http_client()
    url = "https://api.uigf.org/translate/"
    body = {
        "lang": "zh-cn",
        "type": "normal",
        "game": "genshin",
        "item_name": name
    }
    response = http_client.post_json(
        url,
        body=body,
        context=f"Failed to query UIGF item id name={name}",
        retry=True,
    )
    logger.debug("%s[API] UIGF API result: %s -> %s", Fore.BLUE, name, response.payload)
    item_id = response.payload.get("item_id")
    if type(item_id) is not int:
        raise ValueError(
            f"UIGF item lookup returned invalid item_id name={name}: {item_id!r}"
        )
    return item_id


def resolve_item_ids(
    names: list[str],
    cache: dict[str, int],
    client: HttpClient,
) -> list[int]:
    resolved: list[int] = []
    for name in names:
        if name not in cache:
            cache[name] = get_item_id_by_name(name, client)
        resolved.append(cache[name])
    return resolved


def get_banner_name_by_subtitle(subtitle: str) -> str:
    # CHS
    subtitle = subtitle.replace("」祈愿", "")
    subtitle = subtitle.replace("「", "")
    # EN-US
    subtitle = subtitle.replace("Event Wish - ", "")
    # CHT
    subtitle = subtitle.replace("」祈願", "")
    subtitle = subtitle.replace("「", "")
    # JP
    subtitle = subtitle.replace(r"イベント祈願<br />", "")
    subtitle = subtitle.replace("集録祈願<br />", "")
    subtitle = subtitle.replace("」", "")
    # KO
    subtitle = subtitle.replace("「", "")
    subtitle = subtitle.replace("」 기원", "")
    subtitle = subtitle.replace(" 기원", "")
    # ES
    subtitle = subtitle.replace("Gachapón «", "")
    subtitle = subtitle.replace("»", "")
    # FR
    subtitle = subtitle.replace("Vœux « ", "")
    subtitle = subtitle.replace("Vœux « ", "")
    subtitle = subtitle.replace(" »", "")
    subtitle = subtitle.replace(" ", "")
    # RU
    subtitle = subtitle.replace("Молитва «", "")
    subtitle = subtitle.replace("»", "")
    subtitle = subtitle.replace("Молитва: ", "")
    # TH
    subtitle = subtitle.replace("การอธิษฐาน \"", "")
    subtitle = subtitle.replace("\"", "")
    # VI
    subtitle = subtitle.replace("Cầu Nguyện \"", "")
    subtitle = subtitle.replace("\"", "")
    subtitle = subtitle.replace("Cầu Nguyện ", "")
    # DE
    subtitle = subtitle.replace("Gebet „", "")
    subtitle = subtitle.replace("“", "")
    # ID
    subtitle = subtitle.replace("Event Permohonan \"", "")
    subtitle = subtitle.replace("\"", "")
    subtitle = subtitle.replace("Event Permohonan ", "")
    # PT
    subtitle = subtitle.replace("Oração \"", "")
    subtitle = subtitle.replace("\"", "")
    subtitle = subtitle.replace("Oração ", "")
    # TR
    subtitle = subtitle.replace("\" Etkinliği Dileği", "")
    subtitle = subtitle.replace(" Etkinliği Dileği", "")
    subtitle = subtitle.replace("\"", "")
    # IT
    subtitle = subtitle.replace("Desiderio ", "")
    return subtitle


def announcement_to_banner_meta(
    chs_ann: dict,
    all_announcements: list,
    snapshot: AnnouncementSnapshot,
    item_id_cache: dict[str, int] | None = None,
    client: HttpClient | None = None,
) -> list[BannerMeta] | None:
    """
    Convert an announcement to a list of BannerMeta objects, each list represent a banner in different language.
    Uses the CHS announcement as the base to parse most of the data and other languages data inherit from CHS.
    """
    print_separator()
    http_client = client or get_default_http_client()
    resolved_item_ids = item_id_cache if item_id_cache is not None else {}
    uigf_pool_type = 0

    banner_name = get_banner_name_by_subtitle(chs_ann["subtitle"])  # BannerMeta.name
    banner_image_url = chs_ann.get("banner", "")  # BannerMeta.banner_image_url
    content_text = BeautifulSoup(chs_ann["content"], "html.parser").text
    logger.info("%s[Content] Content text: %s", Fore.GREEN, content_text)
    if "概率UP" in chs_ann["title"]:
        logger.info("")
        if "概率提升角色" in content_text:
            if "※ 本祈愿属于「角色活动祈愿」" in content_text:
                uigf_pool_type = 301
            elif "※ 本祈愿属于「角色活动祈愿-2」" in content_text:
                uigf_pool_type = 400
            # Character Banner
            characters_re_list = re.findall(r"[\u4e00-\u9fa5]+(?=\(风\)|\(火\)|\(水\)|\(冰\)|\(雷\)|\(岩\)|\(草\))", content_text)
            characters_list = []
            [characters_list.append(x) for x in characters_re_list if x not in characters_list]
            characters_id_list = resolve_item_ids(characters_list, resolved_item_ids, http_client)
            logger.info("\n%s[Character Parsing] Characters list: %s", Fore.MAGENTA, characters_list)
            logger.info("%s[Character Parsing] Characters ID list: %s", Fore.MAGENTA, characters_id_list)
            if len(characters_id_list) != 4:
                raise RuntimeError("Character banner must have 4 characters")
            orange_id_list = [characters_id_list[0]]
            purple_id_list = characters_id_list[1:]
            logger.info("%s[Character Parsing] Orange ID: %s", Fore.MAGENTA, orange_id_list)
            logger.info("%s[Character Parsing] Purple ID: %s\n", Fore.MAGENTA, purple_id_list)
        elif "神铸赋形" in chs_ann["subtitle"]:
            uigf_pool_type = 302
            weapon_re_list = re.findall(r"·([\u4e00-\u9fa5]+)", content_text)
            weapon_list = []
            [weapon_list.append(x) for x in weapon_re_list if x not in weapon_list]
            weapon_id_list = resolve_item_ids(weapon_list, resolved_item_ids, http_client)
            logger.info("\n%s[Weapon Parsing] Weapon list: %s", Fore.MAGENTA, weapon_list)
            logger.info("%s[Weapon Parsing] Weapon ID list: %s", Fore.MAGENTA, weapon_id_list)
            if len(weapon_id_list) != 7:
                raise RuntimeError("Weapon banner must have 7 weapons")
            orange_id_list = weapon_id_list[:2]
            purple_id_list = weapon_id_list[2:]
            logger.info("%s[Weapon Parsing] Orange ID: %s", Fore.MAGENTA, orange_id_list)
            logger.info("%s[Weapon Parsing] Purple ID: %s\n", Fore.MAGENTA, purple_id_list)
        else:
            raise RuntimeError("Unknown banner type")
    elif "本祈愿属于「集录祈愿」" in content_text:
        uigf_pool_type = 500
        content_text_no_space = content_text.replace(" ", "")
        orange_characters_re_list = re.search(r"5星角色：(?P<r>.*?)5星武器：", content_text_no_space).group("r").split("/")
        logger.info("%s[Gacha Parsing] Orange characters re list: %s", Fore.CYAN, orange_characters_re_list)
        purple_characters_re_list = re.search(r"4星角色：(?P<r>.*?)(?=4星武器：)", content_text_no_space).group("r").split("/")
        logger.info("%s[Gacha Parsing] Purple characters re list: %s", Fore.CYAN, purple_characters_re_list)
        orange_weapons_re_list = re.search(r"5星武器：(?P<r>.*?)4星角色：", content_text_no_space).group("r").split("/")
        logger.info("%s[Gacha Parsing] Orange weapons re list: %s", Fore.CYAN, orange_weapons_re_list)
        purple_weapons_re_list = re.search(r"4星武器：(?P<r>.*?)(?=※)", content_text_no_space).group("r").split("/")
        logger.info("%s[Gacha Parsing] Purple weapons re list: %s", Fore.CYAN, purple_weapons_re_list)
        orange_list = []
        [orange_list.append(x) for x in orange_characters_re_list if x not in orange_list]
        [orange_list.append(x) for x in orange_weapons_re_list if x not in orange_list]
        purple_list = []
        [purple_list.append(x) for x in purple_characters_re_list if x not in purple_list]
        [purple_list.append(x) for x in purple_weapons_re_list if x not in purple_list]

        orange_id_list = resolve_item_ids(orange_list, resolved_item_ids, http_client)
        purple_id_list = resolve_item_ids(purple_list, resolved_item_ids, http_client)
        logger.info("%s[Gacha Parsing] Orange list: %s", Fore.CYAN, orange_list)
        logger.info("%s[Gacha Parsing] Purple list: %s", Fore.CYAN, purple_list)
        logger.info("%s[Gacha Parsing] Orange ID list: %s", Fore.CYAN, orange_id_list)
        logger.info("%s[Gacha Parsing] Purple ID list: %s", Fore.CYAN, purple_id_list)
        logger.info("%s[Gacha Parsing] Total count of Orange: %s", Fore.CYAN, len(orange_id_list))
        logger.info("%s[Gacha Parsing] Total count of Purple: %s\n", Fore.CYAN, len(purple_id_list))
    else:
        logger.info("%s[Content] Not a banner announcement: %s\n", Fore.LIGHTYELLOW_EX, chs_ann["subtitle"])
        return None

    if uigf_pool_type != 0:
        if uigf_pool_type != 500:
            time_pattern = (r"(?:〓祈愿介绍〓祈愿时间概率提升(?:角色|武器)（5星）概率提升(?:角色|武器)（4星）"
                            r"(<t class=\"(?:(t_lc)|(t_gl))\">)?)"
                            r"(?P<start>((\d\.\d|「月之[一二三四五六七八九]」)版本更新后)|(20\d{2}/\d{2}/\d{2} \d{2}:\d{2}(:\d{2})?))"
                            r"(?:(</t>)?( )?~( )?<t class=\"(?:(t_lc)|(t_gl))\">)"
                            r"(?P<end>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}(:\d{2})?)")
        else:
            time_pattern = (r"(?:〓祈愿介绍〓祈愿时间可定轨5星角色可定轨5星武器"
                            r"(<t class=\"(?:(t_lc)|(t_gl))\">)?)"
                            r"(?P<start>((\d\.\d|「月之[一二三四五六七八九]」)版本更新后)|(20\d{2}/\d{2}/\d{2} \d{2}:\d{2}(:\d{2})?))"
                            r"(?:(</t>)?( )?~( )?<t class=\"(?:(t_lc)|(t_gl))\">)"
                            r"(?P<end>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}(:\d{2})?)")
        try:
            content_text = content_text.replace(' contenteditable="false"', "")
            time_result = re.search(time_pattern, content_text)
            start_time = time_result.group("start")
            end_time = time_result.group("end")
            logger.info("%s[Time Parsing] Found banner time: %s ~ %s", Fore.LIGHTRED_EX, start_time, end_time)
        except AttributeError as exc:
            raise ValueError(
                f"Unknown time format\nAnnouncement Content: {content_text}\nPattern: {time_pattern}"
            ) from exc
        if "更新后" in start_time:
            order = 1
            logger.debug(
                "%s[Time Parsing] Start time is relative, need to find accurate time in update log",
                Fore.LIGHTRED_EX,
            )
            version_match = re.search(r"^(\d\.\d|「月之[一二三四五六七八九]」)", start_time)
            if version_match:
                version_text = version_match.group(0)
                if "月之" in version_text:
                    version = convert_chinese_version(version_text)
                else:
                    version = version_text
            else:
                raise ValueError(f"Unknown version format in start_time: {start_time}")

            try:
                patch_notes = [b for b in all_announcements if
                              (b["subtitle"] == version + "版本更新说明") or
                              (any(chinese + "版本更新说明" in b["subtitle"] for chinese in CHINESE_VERSION_MAP.keys()))]
                if patch_notes:
                    patch_note = BeautifulSoup(patch_notes[0]["content"], "html.parser").text
                    patch_time_pattern = (r"(?:〓更新时间〓<t class=\"t_(gl|lc)\"( contenteditable=\"false\")?>)"
                                          r"(?P<start>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}(:\d{2})?)"
                                          r"(?:</t>开始)")
                else:
                    raise IndexError("No patch notes found")
            except IndexError:
                try:
                    patch_notes = [b for b in all_announcements if
                                  (b["subtitle"] == version + "版本更新维护预告") or
                                  (any(chinese + "版本更新维护预告" in b["subtitle"] for chinese in CHINESE_VERSION_MAP.keys()))]
                    if patch_notes:
                        patch_note = BeautifulSoup(patch_notes[0]["content"], "html.parser").text
                        logger.info("\n%s[Patch Note] Patch note: %s", Fore.LIGHTBLUE_EX, patch_note)
                        patch_time_pattern = (r"(?:预计将于<t class=\"t_(gl|lc)\"( contenteditable=\"false\")?>)"
                                              r"(?P<start>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}(:\d{2})?)"
                                              r"(?:</t>进行版本更新维护)")
                    else:
                        raise IndexError("No maintenance announcement found")
                except IndexError:
                    for b in all_announcements:
                        logger.debug("%s[Debug] %s", Fore.RED, b["subtitle"])
                        logger.debug("%s[Debug] %s", Fore.RED, b["content"])
                    logger.info(
                        "%s[Patch Note] No update log found; game is most likely under maintenance",
                        Fore.LIGHTBLUE_EX,
                    )
                    sys.exit(500)
            try:
                start_time = re.search(patch_time_pattern, patch_note).group("start")
            except AttributeError as exc:
                raise ValueError(
                    f"Unknown time format\nPatch Note: {patch_note}\nPattern: {patch_time_pattern}"
                ) from exc
            logger.info("%s[Patch Note] Found patch time: %s", Fore.LIGHTBLUE_EX, start_time)
        else:
            version = "99.99"
            order = 2
            for b in all_announcements:
                if "版本更新说明" in b["subtitle"]:
                    version_match = re.search(r"^(\d+\.\d+|「月之[一二三四五六七八九]」)", b["subtitle"])
                    if version_match:
                        version_text = version_match.group(0)
                        if "月之" in version_text:
                            version = convert_chinese_version(version_text)
                        else:
                            version = version_text
                    break
            if version == "99.99":
                raise ValueError("No update log found")
    else:
        return None

    banner_meta = BannerMeta(
        lang="zh-cn",
        ann_id=chs_ann["ann_id"],
        version=version,
        order=order,
        name=banner_name,
        uigf_banner_type=uigf_pool_type,
        banner_image_url=banner_image_url,
        banner_image_url_backup=banner_image_url,
        start_time=start_time,
        end_time=end_time,
        up_orange_list=orange_id_list,
        up_purple_list=purple_id_list
    )
    logger.info("\n%s[BannerMeta] %s", Fore.LIGHTGREEN_EX, banner_meta.model_dump_json())
    return localize_banner_meta(banner_meta, snapshot)


def localize_banner_meta(
    chinese_meta: BannerMeta,
    snapshot: AnnouncementSnapshot,
) -> list[BannerMeta]:
    """Build every locale from a Chinese banner, falling back when localization lags."""
    banner_meta_list = [chinese_meta]
    for language in TARGET_LANGUAGES:
        localized_meta = chinese_meta.model_copy()
        localized_meta.lang = language
        matched_announcement = snapshot.by_id[language].get(chinese_meta.ann_id)
        if matched_announcement is None:
            logger.warning(
                "Missing localized banner announcement language=%s ann_id=%s; "
                "falling back to zh-cn name and image",
                language,
                chinese_meta.ann_id,
            )
        else:
            localized_meta.name = get_banner_name_by_subtitle(
                matched_announcement["subtitle"]
            )
            localized_meta.banner_image_url = matched_announcement.get("banner", "")
        logger.info(
            "%s[BannerMeta] %s",
            Fore.LIGHTGREEN_EX,
            localized_meta.model_dump_json(),
        )
        banner_meta_list.append(localized_meta)

    return banner_meta_list


def _write_archive_file(path: Path, content: str, *, language: str, announcement_id: int) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError:
        logger.exception(
            "Failed to archive announcement language=%s ann_id=%s path=%s",
            language,
            announcement_id,
            path,
        )
        raise


def archive_announcement(ann: dict, snapshot: AnnouncementSnapshot) -> None:
    announcement_id = ann["ann_id"]
    announcement_dir = Path("ann_archive") / str(announcement_id)
    _write_archive_file(
        announcement_dir / "zh-cn.txt",
        ann["content"],
        language="zh-cn",
        announcement_id=announcement_id,
    )

    for language in TARGET_LANGUAGES:
        localized = snapshot.by_id[language].get(announcement_id)
        if localized is None:
            logger.warning(
                "Missing archive announcement language=%s ann_id=%s",
                language,
                announcement_id,
            )
            continue
        _write_archive_file(
            announcement_dir / f"{language}.txt",
            localized["content"],
            language=language,
            announcement_id=announcement_id,
        )


def update_banner_announcement_list(
    announcement_ids: list[int],
    path: Path = Path("ann_archive/banner_ann_list.txt"),
) -> None:
    try:
        existing_ids = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        ordered_ids: list[str] = []
        seen: set[str] = set()
        for announcement_id in [*existing_ids, *(str(value) for value in announcement_ids)]:
            normalized_id = announcement_id.strip()
            if normalized_id and normalized_id not in seen:
                seen.add(normalized_id)
                ordered_ids.append(normalized_id)

        serialized = "".join(f"{announcement_id}\n" for announcement_id in ordered_ids)
        if path.exists() and path.read_text(encoding="utf-8") == serialized:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
    except OSError:
        logger.exception("Failed to update banner announcement list path=%s", path)
        raise


def refresh_all_banner_data(client: HttpClient | None = None) -> None:
    http_client = client or get_default_http_client()
    return_result = {}
    item_id_cache: dict[str, int] = {}
    banner_announcement_ids: list[int] = []
    url = f"{ANNOUNCEMENT_URL}?{urlencode(announcement_params('zh-cn'))}"
    logger.info("%s[HTTP] zh-cn URL: %s\n", Fore.YELLOW, url)
    snapshot = fetch_announcement_snapshot(http_client)
    banner_data = snapshot.ordered["zh-cn"]
    for ann in banner_data:
        # Archive each announcement's raw content
        archive_announcement(ann, snapshot)
        this_banner_data = announcement_to_banner_meta(
            ann,
            banner_data,
            snapshot,
            item_id_cache,
            http_client,
        )
        if this_banner_data is None:
            continue
        else:
            banner_announcement_ids.append(ann["ann_id"])
            this_banner_dict = {}
            this_banner_ann_id = this_banner_data[0].ann_id

            this_banner_dict["UpOrangeList"] = this_banner_data[0].up_orange_list
            this_banner_dict["UpPurpleList"] = this_banner_data[0].up_purple_list
            this_banner_dict["UIGF_pool_type"] = this_banner_data[0].uigf_banner_type
            this_banner_dict["start_time"] = this_banner_data[0].start_time
            this_banner_dict["end_time"] = this_banner_data[0].end_time
            this_banner_dict["version_number"] = this_banner_data[0].version
            this_banner_dict["order_number"] = this_banner_data[0].order
            for lang_banner in this_banner_data:
                this_banner_dict[lang_banner.lang] = {
                    "banner_name": lang_banner.name,
                    "banner_image": lang_banner.banner_image_url
                }
            return_result[this_banner_ann_id] = this_banner_dict
    try:
        Path("banner-data.json").write_text(
            json.dumps(return_result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        update_banner_announcement_list(banner_announcement_ids)
    except OSError:
        logger.exception("Failed to write generated banner data")
        raise
    logger.info("%s[Finish] Done\n", Fore.LIGHTGREEN_EX)


def run() -> None:
    configure_logging()
    run_mode = validate_run_mode(RUN_MODE)
    logger.info(
        "%s%s======== Starting Banner Data Collection ========%s\n",
        Back.WHITE,
        Fore.BLACK,
        Style.RESET_ALL,
    )
    shared_http_client = get_default_http_client()
    refresh_all_banner_data(shared_http_client)
    create_banner(run_mode, client=shared_http_client)


if __name__ == "__main__":
    try:
        run()
    except Exception:
        logger.exception("Banner data collection failed")
        raise
