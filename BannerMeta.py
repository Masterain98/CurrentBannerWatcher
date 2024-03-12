from pydantic import BaseModel


class BannerMeta(BaseModel):
    lang: str
    ann_id: int

    version: str
    order: int
    name: str
    uigf_banner_type: int
    banner_image_url: str
    banner_image_url_backup: str | None
    start_time: str
    end_time: str

    up_orange_list: list
    up_purple_list: list
