import json
import logging
import os
import warnings
from pathlib import Path

from banner_constants import LANGUAGE_TO_LOCALE
from banner_downloader import cache_banner_images, cache_image_urls
from banner_publisher import publish_banner_data, publish_legacy_banner
from banner_transform import transform_banner_data
from http_client import HttpClient, get_default_http_client
from logging_config import configure_logging


logger = logging.getLogger(__name__)


def update_banner(client: HttpClient | None = None) -> None:
    """Deprecated interactive banner updater kept for backward compatibility."""
    warnings.warn(
        "update_banner() is deprecated and retained only for backward compatibility",
        DeprecationWarning,
        stacklevel=2,
    )
    http_client = client or get_default_http_client()
    url = os.getenv("POST_ENDPOINT")
    if url is None:
        raise AttributeError("POST_ENDPOINT is not set.")

    with Path("banner-data.json").open("r", encoding="utf-8") as file:
        data = json.load(file)

    downloaded_images: set[str] = set()
    for announcement_id, banner in data.items():
        logger.info("Current ann_id: %s", announcement_id)
        logger.info("Sample data: %s", banner["zh-cn"])
        version_input = input("Please enter [Version]: ")
        order_input = input("Please enter [Order] (1,2,3): ")
        type_input = input("Please enter [UIGF-Type] 301(1)/400(2)/302(w): ")
        for language in LANGUAGE_TO_LOCALE:
            language_data = banner.get(language)
            if not isinstance(language_data, dict):
                continue
            body = {
                "version": version_input,
                "locale": LANGUAGE_TO_LOCALE[language],
                "order": int(order_input),
                "type": int(type_input),
                "name": language_data["banner_name"],
                "banner": language_data["banner_image"],
            }
            publish_legacy_banner(
                url,
                body,
                language=language,
                client=http_client,
            )
            image_url = language_data["banner_image"]
            if image_url not in downloaded_images:
                cache_image_urls([image_url], http_client)
                downloaded_images.add(image_url)


def create_banner(
    mode: str = "production",
    client: HttpClient | None = None,
) -> None:
    http_client = client or get_default_http_client()
    with Path("banner-data.json").open("r", encoding="utf-8") as file:
        data = json.load(file)

    new_data = transform_banner_data(data)
    cache_banner_images(new_data, http_client)

    logger.info("%s", new_data)
    with Path("post-data.json").open("w", encoding="utf-8") as outfile:
        json.dump(new_data, outfile, indent=2, ensure_ascii=False)

    if mode == "production":
        endpoint_template = os.getenv("CREATION_POST_ENDPOINT")
        if endpoint_template is None:
            raise AttributeError("CREATION_POST_ENDPOINT env is not set.")
        publish_banner_data(new_data, endpoint_template, http_client)


if __name__ == "__main__":
    try:
        configure_logging()
        create_banner(os.getenv("run_mode"))
        # update_banner()
    except Exception:
        logger.exception("Banner publishing failed")
        raise
