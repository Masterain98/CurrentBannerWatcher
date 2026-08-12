from typing import Any

from banner_constants import GENERIC_METADATA_FIELDS, LANGUAGES


def transform_banner_data(data: dict[str, dict[str, Any]]) -> dict[str, list[list[dict[str, Any]]]]:
    if not data:
        raise ValueError("banner-data.json contains no banners")

    new_data: dict[str, list[list[dict[str, Any]]]] = {language: [] for language in LANGUAGES}
    for announcement_id, banner in data.items():
        missing_fields = [field for field in GENERIC_METADATA_FIELDS if field not in banner]
        if missing_fields:
            raise ValueError(
                f"Banner ann_id={announcement_id} is missing metadata fields: "
                f"{', '.join(missing_fields)}"
            )
        generic_metadata = {field: banner[field] for field in GENERIC_METADATA_FIELDS}
        for language in LANGUAGES:
            language_data = banner.get(language)
            if not isinstance(language_data, dict):
                raise ValueError(
                    f"Banner ann_id={announcement_id} has no object data for language={language}"
                )

            this_post = generic_metadata | language_data
            this_post["Name"] = this_post.pop("banner_name")
            this_post["Version"] = this_post.pop("version_number")
            this_post["Order"] = this_post.pop("order_number")
            this_post["Banner"] = this_post.pop("banner_image")
            this_post["Banner2"] = this_post["Banner"].replace(
                "sdk.hoyoverse.com",
                "cnb.cool/DGP-Studio/CurrentBannerWatcher/-/git/raw/main",
            )
            this_post["From"] = this_post.pop("start_time").replace("/", "-").replace(" ", "T")
            this_post["To"] = this_post.pop("end_time").replace("/", "-").replace(" ", "T")
            this_post["Type"] = this_post.pop("UIGF_pool_type")
            new_data[language].append([this_post])

    return new_data
