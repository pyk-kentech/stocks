from __future__ import annotations

import json
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
        req = Request(
            url,
            data=json.dumps(
                {
                    "grant_type": grant_type,
                    "appkey": appkey,
                    "secretkey": secretkey,
                }
            ).encode("utf-8"),
            headers={"Content-Type": content_type},
            method="POST",
        )
        opener = build_opener(ProxyHandler({}))
        try:
            response = opener.open(req, timeout=timeout_seconds)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            body = json.loads(raw.decode("utf-8")) if raw else {}
            return {
                "status_code": response.status,
                "body_json": body,
            }
