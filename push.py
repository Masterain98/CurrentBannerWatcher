import requests
import json
import os


def update_banner():
    url = os.getenv("POST_ENDPOINT")
    if url is None:
        raise ValueError("POST_ENDPOINT is not set.")
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
                "name": data["banner_subtitle"],
                "banner": data["banner_image"]
            }
            print("Sending data: " + str(body))
            result = requests.post(url, json=body)
            print("Result: " + str(result.status_code) + "\n" + "=" * 20)
            image_data = requests.get(data["banner_image"])
            os.makedirs(os.path.dirname(data["banner_image"].replace('https://sdk.hoyoverse.com/', "")), exist_ok=True)
            open(data["banner_image"].replace('https://sdk.hoyoverse.com/', ""), 'wb').write(image_data.content)


def create_banner():
    pass
