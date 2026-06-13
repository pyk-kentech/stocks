INLINE_CSS = """
:root{color-scheme:light;--ink:#18212b;--muted:#5e6b78;--line:#d7dde3;--bg:#f4f6f8;--panel:#fff;--info:#2f6f9f;--warning:#9a6800;--high:#b4481d;--critical:#a5262d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 Arial,sans-serif}
header,main,footer{max-width:1200px;margin:auto;padding:20px}header{padding-top:30px}h1,h2{margin:0 0 8px;letter-spacing:0}
.meta,.summary{color:var(--muted)}.section{background:var(--panel);border:1px solid var(--line);border-radius:6px;margin:14px 0;padding:16px}
.badge{display:inline-block;color:#fff;border-radius:4px;padding:2px 7px;font-size:11px;font-weight:bold}.INFO{background:var(--info)}.WARNING{background:var(--warning)}.HIGH{background:var(--high)}.CRITICAL{background:var(--critical)}
table{width:100%;border-collapse:collapse;margin-top:10px}th,td{border-bottom:1px solid var(--line);padding:7px;text-align:left;vertical-align:top}th{background:#eef1f4}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f7f8fa;border:1px solid var(--line);padding:10px}details{margin-top:8px}footer{color:var(--muted)}
"""
