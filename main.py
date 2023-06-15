import requests
import re
import json

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
    print(url)
    data = requests.get(url).json().get("data").get("list")
    for ann in data:
        this_result = {
            "banner_name": "",
            "banner_image": "",
            "ann_id": "",
            "five_star_item_1": "",
            "five_star_item_2": "",
            "four_star_item_1": "",
            "four_star_item_2": "",
            "four_star_item_3": "",
            "four_star_item_4": "",
            "four_star_item_5": ""
        }
        if ann["ann_id"] in banner_ann_id or this_keyword_dict.get("title_keyword") in ann["title"]:
            # print(language + " " + ann["title"] + " " + str(ann["ann_id"]) + " " + str(banner_ann_id))
            this_result["banner_image"] = ann["banner"]
            this_result["ann_id"] = ann["ann_id"]
            this_result["subtitle"] = i18n_subtitle(ann["subtitle"])
            if language == "zh-cn":
                this_result["banner_name"] = ann["subtitle"].replace("」祈愿", "").replace("「", "")
                banner_ann_id.append(ann["ann_id"])
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
            return_result.append(this_result)
    return return_result


if __name__ == "__main__":
    result = {}
    output = {}
    banner_ann_id = []
    target_language = ["zh-cn", "en-us", "zh-tw", "ja", "ko", "es", "fr",
                       "ru", "th", "vi", "de", "id", "pt", "tr", "it"]
    for lang in target_language:
        result[lang] = get_data(lang)

    for ann_id in banner_ann_id:
        output[ann_id] = {}
        for lang in target_language:
            output[ann_id][lang] = {}

    for lang in target_language:
        data = result[lang]
        print("================\n%s language data: %s" % (lang, data))
        for banner in data:
            ann_id = banner["ann_id"]
            print("processing banner: %s" % banner)
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
            output[ann_id][lang]["banner_image"] = banner["banner_image"]
            output[ann_id][lang]["banner_subtitle"] = banner["subtitle"]

    with open("output.json", "w", encoding="utf-8") as outfile:
        json.dump(output, outfile, indent=2, ensure_ascii=False)
