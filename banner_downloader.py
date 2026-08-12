from collections.abc import Iterable
from pathlib import Path
from typing import Any

from http_client import HttpClient


IMAGE_URL_PREFIX = "https://sdk.hoyoverse.com/"


def image_destination(image_url: str) -> Path:
    return Path(image_url.replace(IMAGE_URL_PREFIX, ""))


def cache_image_urls(image_urls: Iterable[str], client: HttpClient) -> None:
    downloaded: set[str] = set()
    for image_url in image_urls:
        if image_url in downloaded:
            continue
        downloaded.add(image_url)
        client.download_file(
            image_url,
            image_destination(image_url),
            context=f"Failed to download banner image url={image_url}",
        )


def cache_banner_images(
    post_data: dict[str, list[list[dict[str, Any]]]],
    client: HttpClient,
) -> None:
    image_urls = (
        wrapper[0]["Banner"]
        for banners in post_data.values()
        for wrapper in banners
    )
    cache_image_urls(image_urls, client)
