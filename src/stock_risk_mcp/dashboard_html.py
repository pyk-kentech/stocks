from __future__ import annotations

import json
from html import escape

from stock_risk_mcp.dashboard_assets import INLINE_CSS
from stock_risk_mcp.dashboard_models import DashboardSection, DashboardType
from stock_risk_mcp.notifications import SEVERITY_RANK


DISCLAIMER = "This dashboard is for paper trading and research monitoring only. It is not financial advice and does not guarantee performance."


def render_dashboard_html(title: str, dashboard_type: DashboardType, sections: list[DashboardSection]) -> str:
    ordered = sorted(sections, key=lambda item: -SEVERITY_RANK[item.severity])
    content = "".join(
        f'<section class="section"><span class="badge {item.severity.value}">{item.severity.value}</span>'
        f"<h2>{escape(item.title)}</h2><p class=\"summary\">{escape(item.summary)}</p>{item.html}</section>"
        for item in ordered
    )
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{escape(title)}</title><style>{INLINE_CSS}</style></head><body>"
        f"<header><h1>{escape(title)}</h1><p class=\"meta\">{escape(dashboard_type.value)}</p></header>"
        f"<main>{content}</main><footer>{escape(DISCLAIMER)}</footer></body></html>"
    )


def render_table(rows: list[dict], columns: list[str] | None = None) -> str:
    if not rows:
        return "<p>No stored records.</p>"
    columns = columns or list(rows[0].keys())
    head = "".join(f"<th>{escape(str(column))}</th>" for column in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(_display(row.get(column)))}</td>" for column in columns) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_json(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    return f"<details><summary>Structured details</summary><pre>{escape(payload)}</pre></details>"


def _display(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return "" if value is None else str(value)
