import logging
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)

JSON_TIMEOUT = (5, 30)
IMAGE_TIMEOUT = (5, 60)
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)


class HttpClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class JsonHttpResponse:
    payload: dict[str, Any]
    status_code: int
    text: str


def build_read_retry() -> Retry:
    return Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.5,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=frozenset({"GET", "POST"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )


def _build_session(*, retry_reads: bool) -> requests.Session:
    session = requests.Session()
    if retry_reads:
        adapter = HTTPAdapter(max_retries=build_read_retry())
        session.mount("https://", adapter)
        session.mount("http://", adapter)
    return session


class HttpClient:
    def __init__(
        self,
        read_session: requests.Session | None = None,
        write_session: requests.Session | None = None,
    ) -> None:
        self.read_session = read_session or _build_session(retry_reads=True)
        self.write_session = write_session or _build_session(retry_reads=False)

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        context: str,
    ) -> JsonHttpResponse:
        return self._request_json(
            self.read_session,
            "GET",
            url,
            params=params,
            timeout=JSON_TIMEOUT,
            context=context,
        )

    def post_json(
        self,
        url: str,
        *,
        body: Any,
        context: str,
        retry: bool,
    ) -> JsonHttpResponse:
        """POST JSON, retrying only when the caller declares the operation idempotent.

        ``retry=True`` selects the read session and may resend the request body
        after transient failures. Publication and other non-idempotent callers
        must pass ``retry=False``.
        """
        session = self.read_session if retry else self.write_session
        return self._request_json(
            session,
            "POST",
            url,
            json=body,
            timeout=JSON_TIMEOUT,
            context=context,
        )

    def download_file(self, url: str, destination: Path, *, context: str) -> None:
        temporary_path: Path | None = None
        try:
            working_directory = Path.cwd().resolve()
            resolved_destination = destination.resolve()
            if (
                resolved_destination == working_directory
                or not resolved_destination.is_relative_to(working_directory)
            ):
                raise ValueError(
                    f"Download destination must stay inside the working directory: {destination}"
                )

            with self.read_session.get(url, timeout=IMAGE_TIMEOUT, stream=True) as response:
                response.raise_for_status()
                resolved_destination.parent.mkdir(parents=True, exist_ok=True)
                with NamedTemporaryFile(
                    mode="wb",
                    prefix=".banner-download-",
                    dir=resolved_destination.parent,
                    delete=False,
                ) as output:
                    temporary_path = Path(output.name)
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            output.write(chunk)
                temporary_path.replace(resolved_destination)
                temporary_path = None
        except (OSError, requests.RequestException, ValueError) as exc:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    logger.exception(
                        "Failed to remove incomplete download path=%s",
                        temporary_path,
                    )
            logger.exception("%s", context)
            raise HttpClientError(f"{context}: {exc}") from exc

    @staticmethod
    def _request_json(
        session: requests.Session,
        method: str,
        url: str,
        *,
        context: str,
        **kwargs: Any,
    ) -> JsonHttpResponse:
        try:
            response = session.request(method, url, **kwargs)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError(f"expected a JSON object, got {type(payload).__name__}")
            return JsonHttpResponse(
                payload=payload,
                status_code=response.status_code,
                text=response.text,
            )
        except (requests.RequestException, ValueError) as exc:
            logger.exception("%s", context)
            raise HttpClientError(f"{context}: {exc}") from exc


_default_http_client: HttpClient | None = None


def get_default_http_client() -> HttpClient:
    global _default_http_client
    if _default_http_client is None:
        _default_http_client = HttpClient()
    return _default_http_client
