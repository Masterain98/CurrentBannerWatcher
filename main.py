import os
import requests
import re
import json
from bs4 import BeautifulSoup
from push import create_banner
from BannerMeta import BannerMeta

RUN_MODE = os.getenv("run_mode", "production")
DEBUG = True if RUN_MODE == "debug" else False


def get_item_id_by_name(name: str) -> int:
    url = "https://api.uigf.org/translate/"
    body = {
        "lang": "zh-cn",
        "type": "normal",
        "game": "genshin",
        "item_name": name
    }
    this_result = requests.post(url, json=body)
    if DEBUG:
        print(f"UIGF API result: {name} -> {this_result.json()}")
    try:
        return this_result.json().get("item_id")
    except KeyError:
        return 0


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


def announcement_to_banner_meta(chs_ann: dict, all_announcements: list) -> list[BannerMeta] | None:
    """
    Convert an announcement to a list of BannerMeta objects, each list represent a banner in different language.
    Uses the CHS announcement as the base to parse most of the data and other languages data inherit from CHS.
    :param all_announcements: all announcements data
    :param chs_ann: Full announcement data
    :return: List of BannerMeta objects
    """
    banner_meta_list = []
    uigf_pool_type = 0

    banner_name = get_banner_name_by_subtitle(chs_ann["subtitle"])  # BannerMeta.name
    banner_image_url = chs_ann.get("banner", "")  # BannerMeta.banner_image_url
    content_text = BeautifulSoup(chs_ann["content"], "html.parser").text
    print(f"Content text: {content_text}")
    if "概率UP" in chs_ann["title"]:
        # 概率UP -> Banner type 200, 301, 400, 302
        if "概率提升角色" in content_text:
            if "※ 本祈愿属于「角色活动祈愿」" in content_text:
                uigf_pool_type = 301
            elif "※ 本祈愿属于「角色活动祈愿-2」" in content_text:
                uigf_pool_type = 400
            # Character Banner
            characters_re_list = re.findall(r"[\u4e00-\u9fa5]+(?=\(风\)|\(火\)|\(水\)|\(冰\)|\(雷\)|\(岩\)|\(草\))",
                                            content_text)
            # Remove duplicates and keep order
            characters_list = []
            [characters_list.append(x) for x in characters_re_list if x not in characters_list]
            characters_id_list = [get_item_id_by_name(x) for x in characters_list]
            print(f"Characters list: {characters_list}")
            print(f"Characters ID list: {characters_id_list}")
            if len(characters_id_list) != 4:
                raise RuntimeError("Character banner must have 4 characters")
            orange_id_list = [characters_id_list[0]]
            purple_id_list = characters_id_list[1:]
            print(f"Orange ID: {orange_id_list}\nPurple ID: {purple_id_list}")
        elif "神铸赋形" in chs_ann["subtitle"]:
            uigf_pool_type = 302
            weapon_re_list = re.findall(r"·([\u4e00-\u9fa5]+)", content_text)
            # Remove duplicates and keep order
            weapon_list = []
            [weapon_list.append(x) for x in weapon_re_list if x not in weapon_list]
            weapon_id_list = [get_item_id_by_name(x) for x in weapon_list]
            print(f"Weapon list: {weapon_list}")
            print(f"Weapon ID list: {weapon_id_list}")
            if len(weapon_id_list) != 7:
                raise RuntimeError("Weapon banner must have 7 weapons")
            orange_id_list = weapon_id_list[:2]
            purple_id_list = weapon_id_list[2:]
            print(f"Orange ID: {orange_id_list}\nPurple ID: {purple_id_list}")
        else:
            raise RuntimeError("Unknown banner type")
    elif "本祈愿属于「集录祈愿」" in content_text:
        uigf_pool_type = 500
        content_text_no_space = content_text.replace(" ", "")
        orange_characters_re_list = re.search(r"5星角色：(?P<r>[^5星武器：]+)", content_text_no_space).group("r").split("/")
        print(f"Orange characters re list: {orange_characters_re_list}")
        purple_characters_re_list = re.search(r"4星角色：(?P<r>[^4星武器：]+)", content_text_no_space).group("r").split("/")
        print(f"Purple characters re list: {purple_characters_re_list}")
        orange_weapons_re_list = re.search(r"5星武器：(?P<r>[^4星角色：]+)", content_text_no_space).group("r").split("/")
        print(f"Orange weapons re list: {orange_weapons_re_list}")
        purple_weapons_re_list = re.search(r"4星武器：(?P<r>[^※]+)", content_text_no_space).group("r").split("/")
        print(f"Purple weapons re list: {purple_weapons_re_list}")
        # Remove duplicates and keep order
        orange_list = []
        [orange_list.append(x) for x in orange_characters_re_list if x not in orange_list]
        [orange_list.append(x) for x in orange_weapons_re_list if x not in orange_list]
        purple_list = []
        [purple_list.append(x) for x in purple_characters_re_list if x not in purple_list]
        [purple_list.append(x) for x in purple_weapons_re_list if x not in purple_list]

        orange_id_list = [get_item_id_by_name(x) for x in orange_list]
        purple_id_list = [get_item_id_by_name(x) for x in purple_list]
        print(f"Orange list: {orange_list}")
        print(f"Purple list: {purple_list}")
        print(f"Orange ID list: {orange_id_list}")
        print(f"Purple ID list: {purple_id_list}")
    else:
        return None

    if uigf_pool_type != 0:
        # Identify banner time
        if uigf_pool_type != 500:
            time_pattern = (r"(?:〓祈愿介绍〓祈愿时间概率提升(?:角色|武器)（5星）概率提升(?:角色|武器)（4星）"
                            r"(<t class=\"(?:(t_lc)|(t_gl))\">)?)"
                            r"(?P<start>(\d.\d版本更新后)|(20\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}))"
                            r"(?:(</t>)?( )?~( )?<t class=\"(?:(t_lc)|(t_gl))\">)"
                            r"(?P<end>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")
        else:
            time_pattern = (r"(?:〓祈愿介绍〓祈愿时间可定轨5星角色可定轨5星武器"
                            r"(<t class=\"(?:(t_lc)|(t_gl))\">)?)"
                            r"(?P<start>(\d.\d版本更新后)|(20\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}))"
                            r"(?:(</t>)?( )?~( )?<t class=\"(?:(t_lc)|(t_gl))\">)"
                            r"(?P<end>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")
        try:
            content_text = content_text.replace(' contenteditable="false"', "")
            time_result = re.search(time_pattern, content_text)
            start_time = time_result.group("start")
            end_time = time_result.group("end")
            print(f"Found banner time: {start_time} ~ {end_time}")
        except AttributeError:
            raise ValueError(f"Unknown time format\nAnnouncement Content: {content_text}\nPattern: {time_pattern}")
        if "更新后" in start_time:
            order = 1
            # find accurate time in update log
            version = re.search(r"^(\d.\d)", start_time).group(0)
            if DEBUG:
                print(f"Found version_number by keyword (更新后): {version}")
            try:
                # 更新说明
                patch_note = BeautifulSoup([b for b in all_announcements if b["subtitle"] == version +
                                            "版本更新说明"][0]["content"], "html.parser").text
                patch_time_pattern = (r"(?:〓更新时间〓<t class=\"t_(gl|lc)\">)"
                                      r"(?P<start>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"
                                      r"(?:</t>开始)")
            except IndexError:
                try:
                    # 更新预告
                    patch_note = BeautifulSoup([b for b in all_announcements if b["subtitle"] == version +
                                                "版本更新维护预告"][0]["content"], "html.parser").text
                    patch_time_pattern = (r"(?:预计将于<t class=\"t_(gl|lc)\">)"
                                          r"(?P<start>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"
                                          r"(?:</t>进行版本更新维护)")
                except IndexError:
                    if DEBUG:
                        for b in all_announcements:
                            print(b["subtitle"])
                            print(b["content"])
                    print("No update log found; game is most likely under maintenance")
                    exit(500)
            start_time = re.search(patch_time_pattern, patch_note).group("start")
            print(f"Found patch time: {start_time}")
        else:
            version = "99.99"
            order = 2
            for b in all_announcements:
                if "版本更新说明" in b["subtitle"]:
                    version = re.search(r"^(\d+\.\d+)", b["subtitle"]).group(0)
                    break
            if version == "99.99":
                raise ValueError("No update log found")
    else:
        return None

    # Create BannerMeta object
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
    print(banner_meta.json())
    banner_meta_list.append(banner_meta)

    target_language = ["en-us", "zh-tw", "ja", "ko", "es", "fr",
                       "ru", "th", "vi", "de", "id", "pt", "tr", "it"]
    for lang in target_language:
        this_meta = banner_meta.copy()
        this_meta.lang = lang
        url = "https://sg-hk4e-api-static.hoyoverse.com/common/hk4e_global/announcement/api/getAnnContent?"
        params = {
            "game": "hk4e",
            "game_biz": "hk4e_global",
            "region": "os_asia",
            "bundle_id": "hk4e_global",
            "channel_id": "1",
            "level": "55",
            "platform": "pc",
            "lang": lang,
        }
        for k, v in params.items():
            url += f"{k}={v}&"
        url += "uid=100000000"
        this_lang_ann = requests.get(url).json().get("data").get("list")
        matched_ann = [ann for ann in this_lang_ann if ann["ann_id"] == chs_ann["ann_id"]]
        banner_name = get_banner_name_by_subtitle(matched_ann[0]["subtitle"])
        this_meta.name = banner_name
        banner_image = matched_ann[0].get("banner", "")
        this_meta.banner_image_url = banner_image
        print(this_meta.json())
        banner_meta_list.append(this_meta)

    print("-" * 20)
    return banner_meta_list


def refresh_all_banner_data():
    return_result = {}
    url = "https://sg-hk4e-api-static.hoyoverse.com/common/hk4e_global/announcement/api/getAnnContent?"
    params = {
        "game": "hk4e",
        "game_biz": "hk4e_global",
        "region": "os_asia",
        "bundle_id": "hk4e_global",
        "channel_id": "1",
        "level": "55",
        "platform": "pc",
        "lang": "zh-cn",
    }
    for k, v in params.items():
        url += f"{k}={v}&"
    url += "uid=100000000"
    print(f"zh-cn URL: {url}")
    banner_data = requests.get(url).json().get("data").get("list")
    for ann in banner_data:
        this_banner_data = announcement_to_banner_meta(ann, banner_data)  # this is a list
        if this_banner_data is None:
            continue
        else:
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
    with open("banner-data.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(return_result, indent=2, ensure_ascii=False))
    print("Done")


if __name__ == "__main__":
    refresh_all_banner_data()
    create_banner()
