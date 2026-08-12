import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import unidecode
from bs4 import BeautifulSoup
import re
import requests

from PIL import Image
import requests
from io import BytesIO

from metadata_db import get_version_from_end_time


def crawler():
    wish_ann = []
    count = 1
    wish_pool_count = 0
    uid_list = ["1015537", "1015611", "1015613"]
    for uid in uid_list:
        trigger = True
        offset_value = 0
        while trigger:
            # Set url
            url = "https://bbs-api-os.hoyolab.com/community/post/wapi/userPost?size=50&uid=%s&offset=%s" % \
                  (uid, offset_value)
            this_post_list = json.loads(requests.get(url, headers={
                "X-Rpc-Language": "en-us",
                "Accept-Language": "en-US;q=0.9;en;q=0.8"
            }).content.decode("utf-8"))["data"]["list"]
            last_post_id = -1
            for post in this_post_list:
                # if "活动祈愿中获得更多" in str(post):
                if "Boosted Drop Rate for" in str(post):
                    wish_ann.append(post)
                    wish_pool_count += 1
                    print(post)
                last_post_id = int(post["post"]["post_id"])

            # Disable trigger when end of post reached
            if last_post_id == 0 or len(this_post_list) == 0:
                trigger = False
            else:
                offset_value = last_post_id
                print("last_post_id is {}, offset value set to {}, length of post is {}, current step is {}, "
                      "current number of pool is {}".format
                      (last_post_id, offset_value, len(this_post_list), count, wish_pool_count))
            count += 1
            # break

        print("total count: {}".format(count))
        with open("wish.json", "w+", encoding="utf-8") as file:
            json.dump(wish_ann, file, indent=2, ensure_ascii=False)


def parser(post_id: str):
    print("parsing post id：{}".format(post_id))
    url = "https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull?post_id={}&read=1".format(post_id)
    result = json.loads(requests.get(url, headers={
        "X-Rpc-Language": "zh-cn",
        "Accept-Language": "zh-CN;q=0.9;zh;q=0.8"
    }).content.decode("utf-8"))["data"]["post"]["post"]["content"]

    # Modern design; Multiple pools in one article
    soup = BeautifulSoup(result, 'html.parser')
    pool_list = []

    # print(soup.prettify())
    title_list = soup.find_all('h4')
    if len(title_list) == 0:
        title_list = soup.find_all('h2')
        if len(title_list) == 0:
            title_list = soup.find_all(lambda tag: tag.name == "p" and "组建" in tag.text)
            if "「" not in title_list[0]:
                title_list = soup.find_all(lambda tag: tag.name == "p" and "概率UP" in tag.text)
    for h4_title in title_list:
        if len(h4_title.text) < 3:
            break
        this_pool = {}
        try:
            title_name = re.search(r"「.+」(活动)?祈愿", h4_title.text)[0].replace("「", "").replace("」祈愿", "") \
                .replace("」活动", "")
        except TypeError:
            title_name = re.match(r"「.+」(活动)?祈愿", h4_title.text)[0].replace("「", "").replace("」祈愿", "") \
                .replace("」活动", "")
        this_pool["title"] = title_name

        this_slice = h4_title
        while True:
            this_slice = this_slice.next_sibling
            if this_slice is None:
                break
            if "<4" in str(this_slice):
                break
            if "~" in this_slice.text:
                print("Find pool time")
                this_time = re.finditer(r"(\d\.\d版本更新后|\d{4}\/\d{1,2}\/\d{1,2}(\s){1,2}\d{2}:\d{2}(:\d{2})?)(\s)?~(\s)?"
                                        r"(\d{4}\/\d{1,2}\/\d{1,2}(\s){1,2}\d{2}:\d{2}(:\d{2})?)", this_slice.text)
                this_pool["time"] = unidecode.unidecode(''.join(i.group(0) for i in this_time).replace("~", " ~ ")
                                                        .replace("  ~  ", " ~ ")) \
                    .replace("Ban Ben Geng Xin Hou ", "版本更新后")
            if title_name == "神铸赋形":
                # 武器池单池两个限定UP
                if "活动期间" in this_slice.text and ("五星武器" in this_slice.text or "5星武器" in this_slice.text):
                    print("Find 5 star character")
                    this_up_5_character = re.finditer(r"(限定)?(5|五)星武器「[^祈愿]{5,}」", this_slice.text)
                    this_up_5_character = ''.join(i.group(0) for i in this_up_5_character).split("」「")
                    this_pool["5-star"] = [
                        c.replace("「", "").replace("」", "").replace("5星武器", "").replace("五星武器", "")
                        .replace("限定", "")
                        for c in this_up_5_character]
                    print(this_pool["5-star"])
                if "活动期间" in this_slice.text and ("四星武器" in this_slice.text or "4星武器" in this_slice.text):
                    print("Find 4 star character")
                    this_up_4_character = re.finditer(r"(限定)?(4|四)星武器「[^祈愿]{5,}」「[^祈愿]{5,}」", this_slice.text)
                    this_up_4_character = ''.join(i.group(0) for i in this_up_4_character).split("」「")
                    this_pool["4-star"] = [
                        c.replace("「", "").replace("」", "").replace("4星武器", "").replace("四星武器", "")
                        .replace("限定", "")
                        for c in this_up_4_character]
                    print(this_pool["4-star"])
            else:
                # 角色池
                if "活动期间" in this_slice.text and ("五星角色" in this_slice.text or "5星角色" in this_slice.text):
                    print("Find 5 star character")
                    this_up_5_character = re.finditer(r"(限定)?(5|五)星角色「[^祈愿]{5,}」", this_slice.text)
                    this_pool["5-star"] = ''.join(i.group(0) for i in this_up_5_character).replace("限定", "") \
                        .replace("5星角色「", "").replace("」", "").replace("五星角色", "")
                if "活动期间" in this_slice.text and ("四星角色" in this_slice.text or "4星角色" in this_slice.text):
                    print("Find 4 star character")
                    this_up_4_character = re.finditer(r"(限定)?(4|四)星角色「[^祈愿]{5,}」", this_slice.text)
                    this_up_4_character = ''.join(i.group(0) for i in this_up_4_character).split("」「")
                    this_pool["4-star"] = [
                        c.replace("「", "").replace("」", "").replace("4星角色", "").replace("四星角色", "")
                        for c in this_up_4_character]
                    print(this_pool["4-star"])
        pool_list.append(this_pool)
    print(pool_list)
    return pool_list


def img_url_format(url: str):
    try:
        url = url.replace("-private", "")
        # url = re.search(r"(^https://)(.+)(\.)(jpg|jpeg|png|webp)", url)[0]
        url = url.split("?")[0]
    except:
        print("Error url: {}".format(url)
              )
        raise Exception("Error url: {}".format(url))
    return url


def get_remote_image_size(lang: str, url: str):
    try:
        response = requests.get(url)
        response.raise_for_status()

        image_data = BytesIO(response.content)

        img = Image.open(image_data)

        width, height = img.size

        if width < 300 or height < 300:
            pass
        else:
            full_path = url.split(".com")[-1]
            file_name = full_path.split("/")[-1]
            level_path = full_path.replace(file_name, "")
            os.makedirs(f"./history/{lang}{level_path}", exist_ok=True)
            img.save(f"./history/{lang}{full_path}")

        return width, height
    except Exception as e:
        print(f"Error url: {url}, error: {e}")
        return None


def parser_lang(post_id: str, lang: str, source: str = "online"):
    pool_list = []
    if source == "online":
        url = f"https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull?post_id={post_id}&read=1"
        result = json.loads(requests.get(url, headers={
            "X-Rpc-Language": lang,
        }).content.decode("utf-8"))["data"]["post"]["post"]["content"]

        # Modern design; Multiple pools in one article
        soup = BeautifulSoup(result, 'html.parser')
        html = soup.prettify()
        os.makedirs(f"./output/{post_id}/", exist_ok=True)
        with open(f"./output/{post_id}/{lang}.html", "w+", encoding="utf-8") as file:
            file.write(html)
    elif source == "local":
        with open(f"./output/{post_id}/{lang}.html", encoding="utf-8") as file:
            html = file.read()
        html = html.replace("-private", "")
        soup = BeautifulSoup(html, 'html.parser')
    else:
        return None

    # Image
    img_list = soup.find_all("img")
    img_list = [img_url_format(item["src"]) for item in img_list
                if "https://upload-os-bbs.hoyolab.com" in item["src"]
                or "https://hoyolab-upload.hoyolab.com" in item["src"]
                or "https://webstatic.hoyoverse.com" in item["src"]]
    #print(f"img_list ({post_id}/{lang}) length: {len(img_list)}")

    for img in img_list:
        res = get_remote_image_size(lang, img)
        if res is None:
            img_list.remove(img)
            print(f"Removing image: {img}, from /{post_id}/{lang}.html")
        elif res[0] < 300 or res[1] < 300:
            img_list.remove(img)
            print("Removing small image: {}".format(img))
        else:
            pass
            # print("Saving image: {}".format(img))

    # title (banner name)
    banner_name_list = []
    if lang == "de-de":
        available_tags = ["h3", "h4", "strong", "p"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text.replace("\n", "").strip() for item in title_list_basic]
        title_list = [item for item in title_list if "Gebet" in item]
        title_list = [item for item in title_list if item.startswith("Gebet")]
        # print(f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #      if len(title_list) != 3 else "")
        for title in title_list:
            try:
                banner_name = re.search(r"(?:Gebet „)(?P<banner>[^“:]*?)“:", title).group("banner")
            except AttributeError:
                print(title)
                raise AttributeError
            banner_name_list.append(banner_name)
    elif lang == "en-us":
        html_content = soup.text
        banner_name_list = re.findall(r"(?:Event Wish \")(?P<banner>[^\"]*?)(?:\")", html_content)
    elif lang == "es-es":
        available_tags = ["h3", "h4", "p"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text.replace("\n", "").strip() for item in title_list_basic]
        title_list = [item for item in title_list if "Gachapón «" in item or "gachapón «" in item]
        # print(f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #      if len(title_list) != 3 else "")
        for title in title_list:
            banner_name = re.search(r"(?:[G|g]achapón «)(?P<banner>[^»]*?)»", title).group("banner")
            banner_name_list.append(banner_name)
    elif lang == "fr-fr":
        available_tags = ["h3", "h4", "strong"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text for item in title_list_basic if "Vœux" in item.text]
        # print(f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #      if len(title_list) != 3 else "")
        for title in title_list:
            banner_name = re.search(r"(?:Vœux « )(?P<banner>[^»]*?)(?: »)",
                                    title.replace(" ", " ")).group("banner")
            banner_name_list.append(banner_name)
    elif lang == "id-id":
        available_tags = ["h3", "h4", "p"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text.replace("\n", "").strip() for item in title_list_basic]
        title_list = [item for item in title_list if "Event Permohonan" in item]
        title_list = [item for item in title_list if "〓" not in item]
        title_list = [item for item in title_list if item.startswith("Event Permohonan")]
        # print(
        #    f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #    if len(title_list) != 3 else "")
        for title in title_list:
            try:
                banner_name = re.search(r"(?:Event Permohonan [\"]?)(?P<banner>[^\"]*?)\"", title).group("banner")
            except AttributeError:
                try:
                    banner_name = re.search(r"(?:Event Permohonan [\"]?)(?P<banner>[^:]*?):", title).group("banner")
                except AttributeError:
                    print(post_id, title)
                    raise AttributeError
            banner_name_list.append(banner_name)
    elif lang == "it-it":
        available_tags = ["h3", "h4", "p"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text.replace("\n", "").strip() for item in title_list_basic]
        title_list = [item for item in title_list if "※" not in item and "〓" not in item]
        title_list = [item for item in title_list if "Desiderio" in item]
        # print(f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #      if len(title_list) != 3 else "")
        for title in title_list:
            banner_name = re.search(r"(?:Desiderio )(?P<banner>[^:]*?)(?::)", title).group("banner")
            banner_name_list.append(banner_name)
    elif lang == "ja-jp":
        title_list_basic = soup.find_all("p")
        title_list = [item.text for item in title_list_basic if
                      "イベント祈願・「" in item.text and "確率UP" in item.text]
        # print(f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #      if len(title_list) != 3 else "")
        for title in title_list:
            banner_name = re.search(r"(?:イベント祈願・「)(?P<banner>[^」]*?)(?:」)", title).group("banner")
            banner_name_list.append(banner_name)
    elif lang == "ko-kr":
        available_tags = ["h3", "h4", "p"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text for item in title_list_basic if "」 기원" in item.text]
        # print(f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #      if len(title_list) != 3 else "")
        for title in title_list:
            if "신의 주조" in title:
                banner_name = "신의 주조"
            else:
                banner_name = re.search(r"(?:「)(?P<banner>[^」]*?)(?:」 기원)", title).group("banner")
            banner_name_list.append(banner_name)
    elif lang == "pt-pt":
        available_tags = ["h3", "h4", "p"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text.replace("\n", "").strip() for item in title_list_basic]
        title_list = [item for item in title_list if "※" not in item and "〓" not in item]
        title_list = [item for item in title_list if "Oração" in item]
        title_list = [item for item in title_list if item.startswith("Oração")]
        # print(f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #      if len(title_list) != 3 else "")
        for title in title_list:
            banner_name = re.search(r"(?:Oração \")(?P<banner>[^\"]*?)(?:\")", title).group("banner")
            banner_name_list.append(banner_name)
    elif lang == "ru-ru":
        available_tags = ["h3", "h4", "p"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text.replace("\n", "").strip() for item in title_list_basic]
        title_list = [item for item in title_list if "※" not in item]
        title_list = [item for item in title_list if "Молитва" in item]
        title_list = [item for item in title_list if item.startswith("Молитва") and "(" in item]
        # print(f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #      if len(title_list) != 3 else "")
        for title in title_list:
            try:
                banner_name = re.search(r"(?:Молитва[:]? «)(?P<banner>[^»]*?)(?:»)", title).group("banner")
            except AttributeError:
                print(title)
                raise AttributeError
            banner_name_list.append(banner_name)
    elif lang == "th-th":
        available_tags = ["h3", "h4", "p"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text.replace("\n", "").strip() for item in title_list_basic]
        title_list = [item for item in title_list if "※" not in item and "〓" not in item]
        title_list = [item for item in title_list if "การอธิษฐาน" in item]
        title_list = [item for item in title_list if item.startswith("การอธิษฐาน") and '"' in item]
        if post_id == "19181094":
            title_list = [title_list[0], "ใบไม้ร่วงตามสายลม", title_list[1]]
        # print(f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #      if len(title_list) != 3 else "")
        for title in title_list:
            if "ใบไม้ร่วงตามสายลม" in title:
                banner_name = "ใบไม้ร่วงตามสายลม"
            elif "สรรค์สร้างเซียน" in title:
                banner_name = "สรรค์สร้างเซียน"
            else:
                banner_name = re.search(r"(?:การอธิษฐาน \")(?P<banner>[^\"]*?)(?:\")", title).group("banner")
            banner_name_list.append(banner_name)
    elif lang == "tr-tr":
        available_tags = ["h3", "h4", "p"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text.replace("\n", "").strip() for item in title_list_basic]
        title_list = [item for item in title_list if "※" not in item and "〓" not in item]
        title_list = [item for item in title_list if "Dileği" in item and item.startswith('"')]
        # print(f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #      if len(title_list) != 3 else "")
        for title in title_list:
            banner_name = re.search(r"(?:\")(?P<banner>[^\"]*?)(?:\" (?:Etkinliği )?Dileği)",
                                    title).group("banner")
            banner_name_list.append(banner_name)
    elif lang == "vi-vn":
        available_tags = ["h3", "h4", "p"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text.replace("\n", "").strip() for item in title_list_basic]
        title_list = [item for item in title_list if "※" not in item and "〓" not in item]
        title_list = [item for item in title_list if item.startswith("Cầu Nguyện") or item.startswith("Cầu nguyện")]
        # print(f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #      if len(title_list) != 3 else "")
        for title in title_list:
            if "Thân Hình Thần Đúc" in title:
                banner_name = "Thân Hình Thần Đúc"
            else:
                try:
                    banner_name = re.search(r"(?:Cầu [N|n]guyện \")(?P<banner>[^\"]*?)(?:\"[:]?)",
                                            title).group("banner")
                except AttributeError:
                    banner_name = re.search(r"(?:Cầu [N|n]guyện [\"]?)(?P<banner>[^:]*?)(?:\:)[:]?",
                                            title).group("banner")
            banner_name_list.append(banner_name)
    elif lang == "zh-cn":
        available_tags = ["h4", "h2", "h3"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        # print("h4_basic_zh_cn: {}".format(title_list_basic))
        title_list = [item.text for item in title_list_basic if "祈愿" in item.text and "〓" not in item.text]
        # print(
        #    f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}" if len(
        #        title_list) != 3 else "")
        for title in title_list:
            banner_name = re.search(r"(?:「)(?P<banner>[^」]*?)(?:」祈愿)", title).group("banner")
            banner_name_list.append(banner_name)
    elif lang == "zh-tw":
        available_tags = ["h4", "h2", "h3"]
        title_list_basic = []
        for tag in available_tags:
            title_list_basic = soup.find_all(tag)
            if title_list_basic:
                break
        title_list = [item.text for item in title_list_basic if "祈願" in item.text and "〓" not in item.text
                      and "※" not in item.text and item.text.strip().startswith("「")]
        # print(
        #    f"title_list ({post_id}/{lang}): {title_list}\ntitle_list_basic ({post_id}/{lang}): {title_list_basic}"
        #    if len(title_list) != 3 else "")
        for title in title_list:
            banner_name = re.search(r"(?:「)(?P<banner>[^」]*?)(?:」祈願)", title).group("banner")
            banner_name_list.append(banner_name)
    else:
        print("Unknown language: {}".format(lang))

    if img_list:
        if len(banner_name_list) == len(img_list):
            for i in range(len(banner_name_list)):
                this_pool = {
                    "banner_name": banner_name_list[i],
                    "banner_image": img_list[i]
                }
                pool_list.append(this_pool)
        else:
            for i in range(len(img_list)):
                this_pool = {
                    "banner_image": img_list[i]
                }
                pool_list.append(this_pool)
    #print(f"pool_list ({post_id}/{lang}): {pool_list}")
    return pool_list


def clean():
    new_list = []
    with open("wish.json", encoding="utf-8") as f:
        data = json.load(f)
    for pool in data:
        # parser_result = parser(pool["post"]["post_id"])
        cleaned_pool = {
            "post_id": pool["post"]["post_id"],
            "created_at": pool["post"]["created_at"],
            "subject": pool["post"]["subject"],
            "content": pool["post"]["content"],
            "lang": pool["post"]["multi_language_info"]["langs"] if pool["post"]["multi_language_info"] is
                                                                    not None else [],
            "image_list": [image["url"] for image in pool["image_list"]],
            # "data": parser_result
        }
        post_id = pool["post"]["post_id"]
        url = f"https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull?post_id={post_id}&read=1"
        post_detail = json.loads(requests.get(url, headers={
            "X-Rpc-Language": "en-us",
        }).content.decode("utf-8"))["data"]["post"]["post"]
        cleaned_pool["subject"] = BeautifulSoup(post_detail["subject"], 'html.parser').text.replace(" ", " ")
        cleaned_pool["content"] = BeautifulSoup(post_detail["content"], 'html.parser').text.replace(" ", " ")
        try:
            version = re.search(r"(?<=[V|v]ersion )(?P<version>\d\.\d)", cleaned_pool["subject"]).group("version")
        except AttributeError:
            try:
                version = re.search(r"(?<=[V|v]ersion )(?P<version>\d\.\d)", cleaned_pool["content"]).group("version")
            except AttributeError:
                version = "0.0"
        cleaned_pool["version"] = version
        if "Phase III" in cleaned_pool["subject"]:
            cleaned_pool["order"] = 3
        elif "Phase II" in cleaned_pool["subject"]:
            cleaned_pool["order"] = 2
        elif "Phase I" in cleaned_pool["subject"]:
            cleaned_pool["order"] = 1
        else:
            if "17:59" in cleaned_pool["content"]:
                cleaned_pool["order"] = 1
            elif "18:00" in cleaned_pool["content"]:
                cleaned_pool["order"] = 2
            else:
                cleaned_pool["order"] = 0
        new_list.append(cleaned_pool)
    with open("wish_parser.json", "w+", encoding="utf-8") as file:
        json.dump(new_list, file, indent=2, ensure_ascii=False)


def get_details():
    import os
    with open("wish_parser.json", encoding="utf-8") as f:
        data = json.load(f)

    def pool_handler(pool):
        pool["lang_detail"] = {}
        # Multi-language post
        for lang in pool["lang"]:
            this_lang_detail = parser_lang(pool["post_id"], lang, "local")
            # if has three banner, then assign them one by one
            if len(this_lang_detail) == 3:
                this_lang_detail[0]["pool_type"] = "301"
                this_lang_detail[1]["pool_type"] = "400"
                this_lang_detail[2]["pool_type"] = "302"
            elif len(this_lang_detail) == 1:
                if "5-star weapon" in pool["content"] or "Epitome Invocation" in pool["content"]:
                    this_lang_detail[0]["pool_type"] = "302"
                elif 'This is for "Character Event Wish-2."' in pool["content"]:
                    this_lang_detail[0]["pool_type"] = "400"
                elif 'This is for "Character Event Wish."' in pool["content"] \
                    or "the event-exclusive 5-star character" in pool["content"] \
                    or "event-exclusive character" in pool["content"] \
                    or "Ballad in Goblets" in pool["content"]:
                    this_lang_detail[0]["pool_type"] = "301"
                else:
                    this_lang_detail[0]["pool_type"] = "000"
                    print(f"Warning! No pool type found, {pool['post_id']}, {lang}, {pool['image_list'][0]}, {len(this_lang_detail)}\n{pool['content']}")
            elif len(this_lang_detail) == 0:
                pass
            else:
                print(f"Error: {pool['post_id']}, {lang}, has {len(this_lang_detail)} pools")
            pool["lang_detail"][lang] = this_lang_detail
        # Single-language post (en-us)
        if len(pool["lang"]) == 0:
            if len(pool["image_list"]) != 1:
                print(f"Error: {pool['post_id']}, en-us, has {len(pool['image_list'])} pools images")
            if ("the event-exclusive 5-star character" in pool["content"]
                    or "event-exclusive character" in pool["content"]
                    or "5-star promotional character" in pool["content"]
                    or "Ballad in Goblets" in pool["content"]):
                this_pool_type = "301"
            elif "Epitome Invocation" in pool["content"]:
                this_pool_type = "302"
            else:
                this_pool_type = "000"
                print(pool["content"])
                print("Error: {} has no pool type".format(pool["post_id"]))

            pool["lang_detail"]["en-us"] = {
                "banner_image": pool["image_list"][0],
                "pool_type": this_pool_type
            }

        # Fix 0.0 version issue
        if pool["version"] == "0.0":
            re_result = re.search(r"(?P<start>\d{4}[/|-]\d{2}[/|-]\d{2} \d{2}:\d{2}:\d{2})(\s?[-–—]\s?)(?P<end>\d{4}[/|-]\d{2}[/|-]\d{2} \d{2}:\d{2}:\d{2})", pool["content"])
            if re_result is None:
                print("Error: {} has no version".format(pool["post_id"]))
            end_time = re_result.group("end")
            while True:
                this_version = get_version_from_end_time(end_time)
                if this_version is not None:
                    break
                time.sleep(5)
            print("Fixing version: {} to {}".format(pool["version"], this_version))
            pool["version"] = this_version

    with ThreadPoolExecutor(os.cpu_count()) as executor:
        executor.map(pool_handler, data)

    """
    for pool in data:
        pool["lang_detail"] = {}
        for lang in pool["lang"]:
            this_lang_detail = parser_lang(pool["post_id"], lang, "local")
            pool["lang_detail"][lang] = this_lang_detail
    """
    with open("wish_parser_detail.json", "w+", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # crawler()
    # clean()
    get_details()
