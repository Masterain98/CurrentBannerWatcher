import requests
import json
import os


def update_banner():
    url = os.getenv("POST_ENDPOINT")
    if url is None:
        raise AttributeError("POST_ENDPOINT is not set.")
    with open("banner-data.json", "r", encoding="utf-8") as f:
        data = json.loads(f.read())
    for k, v in data.items():
        print("Current ann_id: " + str(k))
        print("Sample data: " + str(v["zh-cn"]))
        version_input = input("Please enter [Version]: ")
        order_input = input("Please enter [Order] (1,2,3): ")
        type_input = input("Please enter [UIGF-Type] 301(1)/400(2)/302(w): ")
        for lang, data in v.items():
            match lang:
                case "zh-cn":
                    locale = "CHS"
                case "en-us":
                    locale = "EN"
                case "zh-tw":
                    locale = "CHT"
                case "ja":
                    locale = "JP"
                case "ko":
                    locale = "KR"
                case "es":
                    locale = "ES"
                case "fr":
                    locale = "FR"
                case "ru":
                    locale = "RU"
                case "th":
                    locale = "TH"
                case "vi":
                    locale = "VI"
                case "de":
                    locale = "DE"
                case "id":
                    locale = "ID"
                case "pt":
                    locale = "PT"
                case "it":
                    locale = "IT"
                case "tr":
                    locale = "TR"
                case __:
                    break
            body = {
                "version": version_input,
                "locale": locale,
                "order": int(order_input),
                "type": int(type_input),
                "name": data["banner_name"],
                "banner": data["banner_image"]
            }
            print("Sending data: " + str(body))
            result = requests.post(url, json=body)
            print("Result: " + str(result.status_code) + "\n" + "=" * 20)
            image_data = requests.get(data["banner_image"])
            os.makedirs(os.path.dirname(data["banner_image"].replace('https://sdk.hoyoverse.com/', "")), exist_ok=True)
            open(data["banner_image"].replace('https://sdk.hoyoverse.com/', ""), 'wb').write(image_data.content)


def create_banner():
    new_data = {}
    url = os.getenv("CREATION_POST_ENDPOINT")
    if url is None:
        raise AttributeError("CREATION_POST_ENDPOINT env is not set.")
    with open("banner-data.json", "r", encoding="utf-8") as f:
        data = json.loads(f.read())
    for lang in list(item for item in list(data.values())[0].keys() if len(item) <= 5):
        new_data[lang] = []
    banner_list = list(data.values())
    for banner in banner_list:
        generic_metadata = {k: banner[k] for k in list(banner.keys()) if len(k) > 5}
        for lang in [k for k in list(banner.keys()) if len(k) <= 5]:
            this_post = generic_metadata.copy()
            this_post = this_post | banner[lang]
            this_post["Name"] = this_post.pop("banner_name")
            this_post["Version"] = this_post.pop("version_number")
            this_post["Order"] = this_post.pop("order_number")
            this_post["Banner"] = this_post.pop("banner_image")
            this_post["Banner2"] = this_post["Banner"].replace("sdk.hoyoverse.com", "jihulab.com/DGP-Studio"
                                                                                    "/CurrentBannerWatcher/-/raw/main")
            this_post["From"] = this_post.pop("start_time").replace("/", "-").replace(" ", "T")
            this_post["To"] = this_post.pop("end_time").replace("/", "-").replace(" ", "T")
            this_post["Type"] = this_post.pop("UIGF_pool_type")
            try:
                this_post["UpOrangeList"] = [this_post["five_star_item_1"], this_post["five_star_item_2"]]
            except KeyError:
                this_post["UpOrangeList"] = [this_post["five_star_item_1"]]
            try:
                this_post["UpPurpleList"] = [this_post["four_star_item_1"], this_post["four_star_item_2"],
                                             this_post["four_star_item_3"], this_post["four_star_item_4"],
                                             this_post["four_star_item_5"]]
            except KeyError:
                this_post["UpPurpleList"] = [this_post["four_star_item_1"], this_post["four_star_item_2"],
                                             this_post["four_star_item_3"]]
            this_post.pop("five_star_item_1")
            try:
                this_post.pop("five_star_item_2")
            except KeyError:
                pass
            this_post.pop("four_star_item_1")
            this_post.pop("four_star_item_2")
            this_post.pop("four_star_item_3")
            this_post.pop("four_star_item_4")
            try:
                this_post.pop("four_star_item_5")
            except KeyError:
                pass
            new_data[lang].append([this_post])

    # Start of Debug #
    print(new_data)
    with open("post-data.json", "w", encoding="utf-8") as outfile:
        json.dump(new_data, outfile, indent=2, ensure_ascii=False)
    # END of Debug #

    for lang in new_data.keys():
        match lang:
            case "zh-cn":
                locale = "CHS"
            case "en-us":
                locale = "EN"
            case "zh-tw":
                locale = "CHT"
            case "ja":
                locale = "JP"
            case "ko":
                locale = "KR"
            case "es":
                locale = "ES"
            case "fr":
                locale = "FR"
            case "ru":
                locale = "RU"
            case "th":
                locale = "TH"
            case "vi":
                locale = "VI"
            case "de":
                locale = "DE"
            case "id":
                locale = "ID"
            case "pt":
                locale = "PT"
            case "it":
                locale = "IT"
            case "tr":
                locale = "TR"
            case __:
                break
        for banner in new_data[lang]:
            print("Sending data: " + str(banner))
            return_result = requests.post(url.format(locale=locale), json=banner)
            print("status_code: " + str(return_result.status_code))
            print("content: " + json.loads(return_result.content.decode("utf-8"))["message"])
