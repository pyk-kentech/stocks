from __future__ import annotations

from datetime import datetime, timedelta

from stock_risk_mcp.kiwoom_readonly_allowlist import KiwoomReadOnlyAllowlist
from stock_risk_mcp.kiwoom_readonly_models import KiwoomEnvironment, KiwoomToken
from stock_risk_mcp.kiwoom_transport import FakeKiwoomTransport, KiwoomTransport


def fake_kiwoom_token() -> KiwoomToken:
    now = datetime(2026, 6, 13, 9)
    return KiwoomToken(
        access_token="fake-local-token", token_type="Bearer", issued_at=now,
        expires_at=now + timedelta(days=1), environment=KiwoomEnvironment.MOCK,
        metadata_json={"fake": True},
    )


class KiwoomRestClient:
    def __init__(
        self,
        transport: KiwoomTransport | None = None,
        token: KiwoomToken | None = None,
        allowlist: KiwoomReadOnlyAllowlist | None = None,
        max_continuation_pages: int = 5,
    ) -> None:
        self.transport = transport or FakeKiwoomTransport()
        self.token = token or fake_kiwoom_token()
        self.allowlist = allowlist or KiwoomReadOnlyAllowlist()
        self.max_continuation_pages = max_continuation_pages

    def request_readonly(self, api_id: str, path: str, body: dict) -> dict:
        try:
            self.allowlist.require(api_id, path)
            records: list[dict] = []
            latest: dict = {}
            continuation_count = 0
            request_body = dict(body)
            for page in range(self.max_continuation_pages):
                headers = {"authorization": f"{self.token.token_type} {self.token.access_token}", "api-id": api_id}
                if latest.get("next-key"):
                    headers["cont-yn"] = "Y"
                    headers["next-key"] = str(latest["next-key"])
                latest = self.transport.post(path, headers, request_body)
                if latest.get("status") == "FAILED" or latest.get("error"):
                    return {"status": "FAILED", "error": str(latest.get("error") or "fake transport error"), "records": [], "continuation_count": continuation_count}
                records.extend(latest.get("records", []))
                if latest.get("cont-yn") != "Y" or not latest.get("next-key"):
                    break
                continuation_count += 1
            result = {
                "status": "COMPLETED",
                "record": latest.get("record"),
                "records": records,
                "continuation_count": continuation_count,
                "continuation": {"cont-yn": latest.get("cont-yn", "N"), "next-key": latest.get("next-key")},
                "error": None,
            }
            return result
        except Exception as exc:
            return {"status": "FAILED", "error": str(exc), "records": [], "continuation_count": 0}
