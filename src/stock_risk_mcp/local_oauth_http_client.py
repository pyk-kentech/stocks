from __future__ import annotations

import json
from urllib.error import URLError
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener


class LocalOAuthHttpClient:
    def issue_token(
        self,
        url: str,
        *,
        content_type: str,
        grant_type: str,
        appkey: str,
        secretkey: str,
        timeout_seconds: int,
    ) -> dict[str, object]:
        request_body = {
            "grant_type": grant_type,
            "appkey": appkey,
            "secretkey": secretkey,
        }
        req = Request(
            url,
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": content_type},
            method="POST",
        )
        opener = build_opener(ProxyHandler({}))
        try:
            response = opener.open(req, timeout=timeout_seconds)
        except HTTPError as error:
            response = error
        except URLError as error:
            return {
                "status_code": None,
                "body_json": {},
                "transport_error_type": type(error).__name__,
                "transport_error_message_redacted": str(error.reason or error).strip() or "URL transport error",
                "request_body_shape": sorted(request_body.keys()),
            }
        except Exception as error:  # pragma: no cover
            return {
                "status_code": None,
                "body_json": {},
                "transport_error_type": type(error).__name__,
                "transport_error_message_redacted": str(error).strip() or "transport error",
                "request_body_shape": sorted(request_body.keys()),
            }
        with response:
            raw = response.read()
            try:
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                body = {"raw_body_redacted": raw.decode("utf-8", errors="replace")[:200]}
            return {
                "status_code": response.status,
                "body_json": body,
                "transport_error_type": None,
                "transport_error_message_redacted": None,
                "request_body_shape": sorted(request_body.keys()),
            }
