from push import create_banner
import json
import requests
import os


def cache_banner_image():
    with open("banner-data.json", "r", encoding="utf-8") as f:
        data = json.loads(f.read())
    banner_list = list(data.values())
    for banner in banner_list:
        for v in banner.values():
            image_data = requests.get(v["banner_image"])
            os.makedirs(os.path.dirname(v["banner_image"].replace('https://sdk.hoyoverse.com/', "")), exist_ok=True)
            open(v["banner_image"].replace('https://sdk.hoyoverse.com/', ""), 'wb').write(image_data.content)


if __name__ == '__main__':
    # create_banner()
    cache_banner_image()
