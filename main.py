import requests
import re
import json
from bs4 import BeautifulSoup
from push import create_banner

keyword_dict = {
    "zh-cn": {
        "title_keyword": "概率UP",
        "character_pool_keyword": "概率提升角色",
        "weapon_pool_keyword": "概率提升武器",
        "character_re_patten": r"[\u4e00-\u9fa5]+(?=\(风\)|\(火\)|\(水\)|\(冰\)|\(雷\)|\(岩\)|\(草\))",
        "weapon_re_patten": r"·([\u4e00-\u9fa5]+)"
    },
    "en-us": {
        "title_keyword": "Event Wish",
        "character_pool_keyword": "Promotional Character",
        "weapon_pool_keyword": "Promotional Weapons",
        "character_re_patten": r"(\"[A-Za-z ]+\")(.+?)(?= \()",
        "weapon_re_patten": r"·([\u4e00-\u9fa5]+)"
    }
}


def get_item_id_by_name(name: str):
    url = "https://api.uigf.org/translate/"
    body = {
        "lang": "zh-cn",
        "type": "normal",
        "game": "genshin",
        "item_name": name
    }
    this_result = requests.post(url, json=body)
    try:
        return this_result.json().get("item_id")
    except KeyError:
        return 0


def i18n_subtitle(subtitle: str):
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


def get_data(language: str):
    version_number = ""
    return_result = []
    this_keyword_dict = keyword_dict.get(language, {"title_keyword": "Masterain"})
    url = "https://sg-hk4e-api-static.hoyoverse.com/common/hk4e_global/announcement/api/getAnnContent?"
    params = {
        "game": "hk4e",
        "game_biz": "hk4e_global",
        "region": "os_asia",
        "bundle_id": "hk4e_global",
        "channel_id": "1",
        "level": "55",
        "platform": "pc",
        "lang": language,
    }
    for k, v in params.items():
        url += f"{k}={v}&"
    url += "uid=100000000"
    print(language + ": " + url)
    banner_data = requests.get(url).json().get("data").get("list")
    for ann in banner_data:
        if ann["ann_id"] in banner_ann_id or this_keyword_dict.get("title_keyword") in ann["title"]:
            # Beginning code of matched announcement
            # print(language + " " + ann["title"] + " " + str(ann["ann_id"]) + " " + str(banner_ann_id))
            this_result = {
                "banner_name": "",
                "banner_image": "",
                "ann_id": "",
                "UIGF_pool_type": 0,
                "five_star_item_1": "",
                "five_star_item_2": "",
                "four_star_item_1": "",
                "four_star_item_2": "",
                "four_star_item_3": "",
                "four_star_item_4": "",
                "four_star_item_5": ""
            }
            print(ann)
            this_result["banner_image"] = ann["banner"]
            this_result["ann_id"] = ann["ann_id"]
            this_result["banner_name"] = i18n_subtitle(ann["subtitle"])
            if language == "zh-cn":
                # zh-cn language is the base language to identify banner metadata
                # Other language will use zh-cn data directly
                # Except banner_image, ann_id and subtitle
                content_text = BeautifulSoup(ann["content"], "html.parser").text
                print(content_text)
                #this_result["banner_name"] = ann["subtitle"].replace("」祈愿", "").replace("「", "")
                banner_ann_id.append(ann["ann_id"])
                # Identify banner type and items
                if this_keyword_dict["character_pool_keyword"] in ann["content"]:
                    # 角色池，单个5星角色和三个4星角色
                    characters_list = re.findall(this_keyword_dict["character_re_patten"], ann["content"])
                    this_result["five_star_item_1"] = {"name": characters_list[0],
                                                       "id": get_item_id_by_name(characters_list[0])}
                    this_result["four_star_item_1"] = {"name": characters_list[1],
                                                       "id": get_item_id_by_name(characters_list[1])}

                    this_result["four_star_item_2"] = {"name": characters_list[2],
                                                       "id": get_item_id_by_name(characters_list[2])}
                    this_result["four_star_item_3"] = {"name": characters_list[3],
                                                       "id": get_item_id_by_name(characters_list[3])}
                    this_result["four_star_item_4"] = {"name": characters_list[4],
                                                       "id": get_item_id_by_name(characters_list[4])}
                if this_keyword_dict["weapon_pool_keyword"] in ann["content"]:
                    weapons_list = re.findall(this_keyword_dict["weapon_re_patten"], ann["content"])
                    this_result["five_star_item_1"] = {"name": weapons_list[0],
                                                       "id": get_item_id_by_name(weapons_list[0])}
                    this_result["five_star_item_2"] = {"name": weapons_list[1],
                                                       "id": get_item_id_by_name(weapons_list[1])}
                    this_result["four_star_item_1"] = {"name": weapons_list[2],
                                                       "id": get_item_id_by_name(weapons_list[2])}
                    this_result["four_star_item_2"] = {"name": weapons_list[3],
                                                       "id": get_item_id_by_name(weapons_list[3])}
                    this_result["four_star_item_3"] = {"name": weapons_list[4],
                                                       "id": get_item_id_by_name(weapons_list[4])}
                    this_result["four_star_item_4"] = {"name": weapons_list[5],
                                                       "id": get_item_id_by_name(weapons_list[5])}
                    this_result["four_star_item_5"] = {"name": weapons_list[6],
                                                       "id": get_item_id_by_name(weapons_list[6])}
                # Identify pool type
                if "※ 本祈愿属于「角色活动祈愿」" in ann["content"]:
                    this_result["UIGF_pool_type"] = 301
                elif "※ 本祈愿属于「角色活动祈愿-2」" in ann["content"]:
                    this_result["UIGF_pool_type"] = 400
                elif "神铸赋形" in ann["subtitle"]:
                    this_result["UIGF_pool_type"] = 302
                else:
                    raise ValueError("Unknown pool type\nAnnouncement Content: " + ann["content"])

                # Identify start time
                time_pattern = (r"(?:〓祈愿介绍〓祈愿时间概率提升(?:角色|武器)（5星）概率提升(?:角色|武器)（4星）"
                                r"(<t class=\"(?:(t_lc)|(t_gl))\">)?)"
                                r"(?P<start>(\d.\d版本更新后)|(20\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}))"
                                r"(?:(</t>)?( )?~ <t class=\"(?:(t_lc)|(t_gl))\">)"
                                r"(?P<end>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")
                try:
                    time_result = re.search(time_pattern, content_text)
                    start_time = time_result.group("start")
                    this_result["start_time"] = start_time
                    end_time = time_result.group("end")
                    this_result["end_time"] = end_time
                except AttributeError:
                    raise ValueError("Unknown time format\nAnnouncement Content: " + content_text)
                if "更新后" in start_time:
                    # find accurate time in update log
                    version_number = re.search(r"^(\d.\d)", start_time).group(0)
                    patch_note = BeautifulSoup([b for b in banner_data if b["subtitle"] == version_number +
                                                "版本更新说明"][0]["content"], "html.parser").text
                    patch_time_pattern = (r"(?:〓更新时间〓<t class=\"t_(gl|lc)\">)"
                                          r"(?P<start>20\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"
                                          r"(?:</t>开始)")
                    patch_time = re.search(patch_time_pattern, patch_note).group("start")
                    this_result["start_time"] = patch_time
                    this_result["version_number"] = version_number
                    this_result["order_number"] = 1
                else:
                    this_result["order_number"] = 2
            return_result.append(this_result)
        else:
            # Announcement not matched for wish event
            pass
    return return_result


if __name__ == "__main__":
    result = {}
    output = {}
    banner_ann_id = []
    target_language = ["zh-cn", "en-us", "zh-tw", "ja", "ko", "es", "fr",
                       "ru", "th", "vi", "de", "id", "pt", "tr", "it"]
    for lang in target_language:
        result[lang] = get_data(lang)

    # banner_ann_id is fulfilled by get_data function
    for ann_id in banner_ann_id:
        output[ann_id] = {}
        for lang in target_language:
            output[ann_id][lang] = {}

    for lang in target_language:
        data = result[lang]
        print("================\n%s language data: %s" % (lang, data))
        for banner in data:
            ann_id = banner["ann_id"]
            if lang == "zh-cn":
                output[ann_id]["five_star_item_1"] = banner["five_star_item_1"]["id"]
                try:
                    output[ann_id]["five_star_item_2"] = banner.get("five_star_item_2").get("id")
                except AttributeError:
                    print("no second 5 star found")
                output[ann_id]["four_star_item_1"] = banner["four_star_item_1"]["id"]
                output[ann_id]["four_star_item_2"] = banner["four_star_item_2"]["id"]
                output[ann_id]["four_star_item_3"] = banner["four_star_item_3"]["id"]
                output[ann_id]["four_star_item_4"] = banner["four_star_item_4"]["id"]
                try:
                    output[ann_id]["four_star_item_5"] = banner.get("four_star_item_5").get("id")
                except AttributeError:
                    print("no 5th 4 star found")
                output[ann_id]["UIGF_pool_type"] = banner["UIGF_pool_type"]
                output[ann_id]["start_time"] = banner["start_time"]
                output[ann_id]["end_time"] = banner["end_time"]
                try:
                    output[ann_id]["version_number"] = banner["version_number"]
                except KeyError:
                    output[ann_id]["version_number"] = "4.0"
                output[ann_id]["order_number"] = banner["order_number"]
            output[ann_id][lang]["banner_image"] = banner["banner_image"]
            output[ann_id][lang]["banner_name"] = banner["banner_name"]

    with open("banner-data.json", "w", encoding="utf-8") as outfile:
        json.dump(output, outfile, indent=2, ensure_ascii=False)

    create_banner()
