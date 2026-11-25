# ui.py
# ------------------------------------------------------------
# Presentation layer: shared CSS and reusable FastHTML
# components. No database access, no routing.
# ------------------------------------------------------------
from fasthtml.common import *
from db import TYPE_ICON

NAV = [
    ("/", "Dashboard"),
    ("/resources", "Resources"),
    ("/bookings", "Bookings"),
    ("/availability", "Availability"),
    ("/reports", "Reports"),
]

CSS = """
:root{--primary:#c41e2e;--dark:#1b1b1f;--muted:#6b6b76;--border:#e4e4ea;
--bg:#f7f7f9;--ok:#1f9d55;--warn:#d98500;--risk:#c41e2e;}
*{box-sizing:border-box;}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--dark);background:var(--bg);line-height:1.55;}
a{color:inherit;text-decoration:none;}
.section-wrap{max-width:1140px;margin:0 auto;padding:0 20px;}
.section-padding{padding:32px 0 56px;}
.site-header{background:#fff;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:20;}
.header-inner{max-width:1140px;margin:0 auto;padding:12px 20px;display:flex;
align-items:center;gap:24px;flex-wrap:wrap;}
.brand{font-weight:800;font-size:18px;letter-spacing:-.3px;}
nav{display:flex;gap:6px;flex-wrap:wrap;}
.nav-link{padding:7px 13px;border-radius:999px;font-size:14px;color:var(--muted);}
.nav-link:hover{background:var(--bg);color:var(--dark);}
.nav-link.active{background:var(--primary);color:#fff;font-weight:600;}
.page-header{background:#fff;border-bottom:1px solid var(--border);padding:28px 0;}
.page-header h1{margin:0 0 4px;font-size:30px;letter-spacing:-.6px;}
.muted{color:var(--muted);margin:0;}
.site-footer{border-top:1px solid var(--border);background:#fff;padding:20px 0;
color:var(--muted);font-size:13px;}
.card{background:#fff;border:1px solid var(--border);border-radius:12px;margin-bottom:22px;overflow:hidden;}
.card-head{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;
justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;}
.card-head h3{margin:0;font-size:17px;}
.card-hint{color:var(--muted);font-size:13px;}
.card-body{padding:20px;}
.card-body.flush{padding:0;}
.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
gap:14px;margin-bottom:22px;}
.stat{background:#fff;border:1px solid var(--border);border-radius:12px;padding:16px 18px;}
.stat .icon{font-size:20px;}
.stat .number{font-size:28px;font-weight:800;letter-spacing:-1px;margin:4px 0 0;}
.stat .label{font-weight:600;font-size:14px;}
.stat .note{color:var(--muted);font-size:12px;margin-top:2px;}
.stat.ok .number{color:var(--ok);} .stat.warn .number{color:var(--warn);}
.stat.risk .number{color:var(--risk);}
table{width:100%;border-collapse:collapse;font-size:14px;}
th,td{padding:11px 16px;text-align:left;border-bottom:1px solid var(--border);vertical-align:middle;}
th{background:#fafafc;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);}
tr:last-child td{border-bottom:none;}
tr:hover{background:#fcfcfd;}
.table-wrap{overflow-x:auto;}
.cell-main{font-weight:600;} .cell-sub{color:var(--muted);font-size:12px;}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600;}
.badge.confirmed{background:#e7f5ec;color:var(--ok);}
.badge.completed{background:#eceef5;color:#4a4a5a;}
.badge.cancelled{background:#fdecee;color:var(--risk);}
.badge.no_show{background:#fff4e0;color:var(--warn);}
.badge.inactive{background:#eceef5;color:var(--muted);}
.btn{display:inline-block;padding:9px 16px;border-radius:8px;border:1px solid transparent;
font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;}
.btn-primary{background:var(--primary);color:#fff;}
.btn-ghost{background:#fff;border-color:var(--border);color:var(--dark);}
.btn-danger{background:#fff;border-color:#f3c2c7;color:var(--risk);}
.btn-sm{padding:5px 11px;font-size:13px;}
.actions{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;}
.alert{padding:12px 16px;border-radius:10px;margin-bottom:18px;font-size:14px;border:1px solid transparent;}
.alert.info{background:#eef4ff;border-color:#cddcff;color:#23417d;}
.alert.ok{background:#e7f5ec;border-color:#bfe4cd;color:#15663a;}
.alert.error{background:#fdecee;border-color:#f3c2c7;color:#8e1522;}
.empty{text-align:center;padding:42px 20px;color:var(--muted);}
.empty .icon{font-size:34px;display:block;margin-bottom:8px;}
.empty h4{margin:0 0 4px;color:var(--dark);}
.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;}
.field{display:flex;flex-direction:column;gap:5px;}
.field.full{grid-column:1/-1;}
.field label{font-size:13px;font-weight:600;}
.field input,.field select,.field textarea{padding:9px 11px;border:1px solid var(--border);
border-radius:8px;font-size:14px;font-family:inherit;background:#fff;}
.field .help{font-size:12px;color:var(--muted);}
.listing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;}
.listing{background:#fff;border:1px solid var(--border);border-radius:12px;padding:18px;}
.listing .icon{font-size:24px;} .listing h4{margin:8px 0 2px;font-size:16px;}
.listing .meta{color:var(--muted);font-size:13px;}
.listing .body{font-size:14px;margin:10px 0;}
.listing .price{font-weight:800;color:var(--primary);}
.chart{width:100%;}
.chart-empty{padding:40px 20px;text-align:center;color:var(--muted);font-size:14px;}
.chart-bar{display:flex;align-items:flex-end;gap:14px;height:220px;padding:22px 4px 0;
border-bottom:1px solid var(--border);}
.bar-col{flex:1;display:flex;flex-direction:column;justify-content:flex-end;height:100%;text-align:center;}
.bar-fill{position:relative;border-radius:6px 6px 0 0;
background:linear-gradient(180deg,var(--primary) 0%,rgba(196,30,46,.5) 100%);}
.bar-value{position:absolute;top:-20px;left:0;right:0;font-size:12px;font-weight:700;}
.bar-label{margin-top:8px;font-size:12px;color:var(--muted);}
.chart-line{width:100%;height:auto;display:block;}
.line-path{fill:none;stroke:var(--primary);stroke-width:2.5;stroke-linejoin:round;}
.line-area{fill:rgba(196,30,46,.10);stroke:none;}
.line-dot{fill:#fff;stroke:var(--primary);stroke-width:2;}
.line-axis{stroke:var(--border);stroke-width:1;}
.line-label{font-size:11px;fill:#6b6b76;}
.chart-note{margin-top:8px;font-size:12px;color:var(--muted);text-align:right;}
.slot{display:inline-block;background:#fdecee;color:var(--risk);border-radius:6px;
padding:3px 9px;font-size:12px;margin:2px 4px 2px 0;font-weight:600;}
.slot.free{background:#e7f5ec;color:var(--ok);}
.filters{display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;}
@media(max-width:768px){.chart-bar{gap:8px}.bar-label{font-size:10px}.page-header h1{font-size:24px}}
"""


# ---------------- basic components ----------------
def Alert(message, kind="info"):
    if not message:
        return None
    return Div(message, cls=f"alert {kind}")


def Empty(title, message="", icon="🗂️"):
    return Div(Span(icon, cls="icon"), H4(title), P(message, cls="muted"), cls="empty")


def Card(title, *body, hint="", flush=False):
    return Div(
        Div(H3(title), Span(hint, cls="card-hint") if hint else None, cls="card-head"),
        Div(*body, cls="card-body flush" if flush else "card-body"),
        cls="card",
    )


def StatItem(icon, value, unit="", label="", note="", tone=""):
    return Div(
        Span(icon, cls="icon"),
        Div(f"{value}{unit}", cls="number"),
        Div(label, cls="label"),
        Div(note, cls="note") if note else None,
        cls=f"stat {tone}".strip(),
    )


def StatsRow(*items):
    return Div(*items, cls="stats-row")


def StatusBadge(status):
    return Span(status.replace("_", " ").title(), cls=f"badge {status}")


def Cell(main, sub=""):
    return Td(Div(main, cls="cell-main"), Div(sub, cls="cell-sub") if sub else None)


def DataTable(headers, rows, empty_msg="No records yet."):
    if not rows:
        return Empty("Nothing here yet", empty_msg)
    return Div(Table(Thead(Tr(*[Th(h) for h in headers])), Tbody(*rows)), cls="table-wrap")


def Field(name, label=None, type="text", value="", help_text="", **kw):
    return Div(
        Label(label or name.replace("_", " ").title(), _for=name),
        Input(type=type, name=name, id=name, value=value, **kw),
        Div(help_text, cls="help") if help_text else None,
        cls="field",
    )


def SelectField(name, options, label=None, value="", blank=""):
    opts = []
    if blank:
        opts.append(Option(blank, value=""))
    for o in options:
        txt, val = (o, o) if not isinstance(o, (list, tuple)) else (o[1], o[0])
        opts.append(Option(txt, value=val, selected=(str(val) == str(value))))
    return Div(
        Label(label or name.replace("_", " ").title(), _for=name),
        Select(*opts, name=name, id=name),
        cls="field",
    )


def TextArea_(name, label=None, value="", full=True):
    return Div(
        Label(label or name.replace("_", " ").title(), _for=name),
        Textarea(value, name=name, id=name, rows=3),
        cls="field full" if full else "field",
    )


def ListingCard(icon, title, meta, body, price, actions=None):
    return Div(
        Span(icon, cls="icon"), H4(title), Div(meta, cls="meta"),
        Div(body, cls="body"), Div(price, cls="price"),
        Div(*(actions or []), cls="actions") if actions else None,
        cls="listing",
    )


# ---------------- charts (pure CSS/SVG, no JS, no CDN) ----------------
def _pairs(data, label_key="label", value_key="value"):
    rows = []
    if not data:
        return rows
    items = list(data.items()) if isinstance(data, dict) else data
    for row in items:
        if isinstance(row, dict):
            label, value = row.get(label_key, ""), row.get(value_key, 0)
        elif isinstance(row, (list, tuple)) and len(row) >= 2:
            label, value = row[0], row[1]
        else:
            label, value = str(len(rows) + 1), row
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.0
        rows.append((str(label), value))
    return rows


def BarChart(data, unit="", label_key="label", value_key="value"):
    rows = _pairs(data, label_key, value_key)
    if not rows:
        return Div("No data for this period.", cls="chart-empty")
    peak = max((v for _, v in rows), default=0) or 1.0
    cols = [
        Div(
            Div(Span(f"{v:g}{unit}", cls="bar-value"), cls="bar-fill",
                style=f"height:{max((v / peak) * 100, 2):.1f}%"),
            Div(lbl, cls="bar-label"),
            cls="bar-col",
        )
        for lbl, v in rows
    ]
    return Div(*cols, cls="chart chart-bar")


def LineChart(data, unit="", height=220, width=720, label_key="label", value_key="value"):
    rows = _pairs(data, label_key, value_key)
    if not rows:
        return Div("No data for this period.", cls="chart-empty")
    pad_x, pad_y = 36, 18
    peak = max((v for _, v in rows), default=0) or 1.0
    n = max(len(rows) - 1, 1)
    plot_w, plot_h = width - pad_x * 2, height - pad_y * 2

    pts, dots, labels = [], [], []
    for i, (lbl, v) in enumerate(rows):
        x = pad_x + (i / n) * plot_w
        y = pad_y + plot_h - (v / peak) * plot_h
        pts.append(f"{x:.1f},{y:.1f}")
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" class="line-dot"/>')
        labels.append(f'<text class="line-label" x="{x:.1f}" y="{height - 2}" text-anchor="middle">{lbl}</text>')

    poly = " ".join(pts)
    area = (f'<polygon class="line-area" points="{pad_x:.1f},{pad_y + plot_h:.1f} {poly} '
            f'{pad_x + plot_w:.1f},{pad_y + plot_h:.1f}"/>')
    baseline = (f'<line class="line-axis" x1="{pad_x}" y1="{pad_y + plot_h:.1f}" '
                f'x2="{pad_x + plot_w:.1f}" y2="{pad_y + plot_h:.1f}"/>')
    path = f'<polyline class="line-path" points="{poly}"/>'
    svg = (f'<svg viewBox="0 0 {width} {height}" class="chart chart-line" aria-label="Trend chart">'
           f'{area}{baseline}{path}{"".join(dots)}{"".join(labels)}</svg>')
    return Div(NotStr(svg), Div(f"Peak: {peak:g}{unit}", cls="chart-note"))


# ---------------- page shell ----------------
def Page(title, subtitle="", *body, active="/", actions=None, cta=None):
    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(f"{title} | Campus Resource Booking"),
            Style(CSS),
        ),
        Body(
            Header(
                Div(
                    A("Campus Booking", href="/", cls="brand"),
                    Nav(*[A(label, href=href, cls="nav-link active" if href == active else "nav-link")
                          for href, label in NAV]),
                    cls="header-inner",
                ),
                cls="site-header",
            ),
            Section(
                Div(
                    H1(title),
                    P(subtitle, cls="muted") if subtitle else None,
                    Div(*actions, cls="actions") if actions else None,
                    cls="section-wrap",
                ),
                cls="page-header",
            ),
            Section(Div(*body, cls="section-wrap"), cls="section-padding"),
            cta if cta else None,
            Footer(Div("Campus Resource Booking — built with FastHTML & SQLite", cls="section-wrap"),
                   cls="site-footer"),
        ),
    )