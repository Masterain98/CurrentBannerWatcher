import logging
from typing import Any

from banner_constants import LANGUAGE_TO_LOCALE
from http_client import HttpClient, JsonHttpResponse


logger = logging.getLogger(__name__)


def _log_publish_response(response: JsonHttpResponse) -> None:
    message = response.payload.get("message")
    logger.info("status_code: %s", response.status_code)
    if message is None:
        logger.warning("Publishing response has no message field")
    else:
        logger.info("content: %s", message)
    logger.info("Full content: %s", response.text)
    logger.info("%s", "=" * 20)


def publish_banner_data(
    post_data: dict[str, list[list[dict[str, Any]]]],
    endpoint_template: str,
    client: HttpClient,
) -> None:
    failures: list[Exception] = []
    for language, banners in post_data.items():
        locale = LANGUAGE_TO_LOCALE[language]
        endpoint = endpoint_template.format(locale=locale)
        for banner in banners:
            logger.info("Sending data: %s", banner)
            logger.info("Publishing locale: %s", locale)
            logger.debug("URL: %s", endpoint)
            try:
                response = client.post_json(
                    endpoint,
                    body=banner,
                    context=f"Failed to publish banner language={language} locale={locale}",
                    retry=False,
                )
                _log_publish_response(response)
            except Exception as exc:
                logger.exception(
                    "Banner publication failed language=%s locale=%s; continuing",
                    language,
                    locale,
                )
                failures.append(exc)

    if failures:
        raise ExceptionGroup("One or more banner publications failed", failures)


def publish_legacy_banner(
    endpoint: str,
    body: dict[str, Any],
    *,
    language: str,
    client: HttpClient,
) -> None:
    logger.info("Sending data: %s", body)
    response = client.post_json(
        endpoint,
        body=body,
        context=f"Failed to update banner language={language}",
        retry=False,
    )
    logger.info("Result: %s\n%s", response.status_code, "=" * 20)
