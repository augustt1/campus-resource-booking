# ui.py
# ------------------------------------------------------------
# Presentation layer: CSS and reusable FastHTML UI components.
# No database access, no routing logic.
# ------------------------------------------------------------
from fasthtml.common import *

# third item = who can see the nav link: "all" or "staff"
NAV = [
    ("/", "Dashboard", "all"),
    ("/resources", "Resources", "all"),
    ("/bookings", "Bookings", "all"),
    ("/availability", "Availability", "all"),
    ("/reports", "Reports", "staff"),
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
.alert.warn{background:#fff6e0;border-color:#f1dca3;color:#7a5200;}
.empty{text-align:center;padding:42px 20px;color:var(--muted);}
.empty .icon{font-size:34px;display:block;margin-bottom:8px;}
.empty h4{margin:0 0 4px;color:var(--dark);}
.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;}
.field{display:flex;flex-direction:column;gap:5px;}
.field.full{grid-column:1/-1;}
.field label{font-size:13px;font-weight:600;}
.field input,.field select,.field textarea{padding:11px 13px;border:1px solid var(--border);
border-radius:10px;font-size:15px;font-family:inherit;background:#fff;color:var(--dark);
height:46px;accent-color:var(--primary);
transition:border-color .15s ease,box-shadow .15s ease,background-color .15s ease;}
.field input:hover,.field select:hover,.field textarea:hover{border-color:#c9c9d3;}
.field input:focus,.field select:focus,.field textarea:focus{outline:none;border-color:var(--primary);
box-shadow:0 0 0 4px rgba(196,30,46,.14);}
.field textarea{height:auto;min-height:96px;}
.field select{appearance:none;-webkit-appearance:none;padding-right:38px;cursor:pointer;
background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b6b76' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
background-repeat:no-repeat;background-position:right 12px center;}
.field input[type=date],.field input[type=time]{font-variant-numeric:tabular-nums;font-weight:600;
letter-spacing:.2px;cursor:pointer;}
.field input[type=date]::-webkit-calendar-picker-indicator,
.field input[type=time]::-webkit-calendar-picker-indicator{cursor:pointer;padding:4px;
border-radius:6px;opacity:.6;transition:opacity .15s ease,background-color .15s ease;}
.field input[type=date]::-webkit-calendar-picker-indicator:hover,
.field input[type=time]::-webkit-calendar-picker-indicator:hover{opacity:1;background-color:rgba(196,30,46,.10);}
.field input[type=date]::-webkit-datetime-edit-fields-wrapper,
.field input[type=time]::-webkit-datetime-edit-fields-wrapper{padding:0;}
.field input::-webkit-datetime-edit-day-field:focus,.field input::-webkit-datetime-edit-month-field:focus,
.field input::-webkit-datetime-edit-year-field:focus,.field input::-webkit-datetime-edit-hour-field:focus,
.field input::-webkit-datetime-edit-minute-field:focus{background:var(--primary);color:#fff;border-radius:4px;}
.field .help{font-size:12px;color:var(--muted);}
.dp{position:relative;}
.dp-trigger{width:100%;height:46px;font-variant-numeric:tabular-nums;display:flex;align-items:center;justify-content:space-between;gap:10px;
padding:0 13px;border:1px solid var(--border);border-radius:10px;background:#fff;color:var(--dark);
font:600 15px/1 inherit;font-family:inherit;cursor:pointer;text-align:left;
transition:border-color .15s ease,box-shadow .15s ease;}
.dp-trigger:hover{border-color:#c9c9d3;}
.dp-trigger:focus-visible,.dp-trigger[aria-expanded=true]{outline:none;border-color:var(--primary);
box-shadow:0 0 0 4px rgba(196,30,46,.14);}
.dp-trigger svg{flex:none;color:var(--muted);}
.dp-pop{position:fixed;z-index:50;width:300px;padding:14px;background:#fff;border:1px solid var(--border);
border-radius:16px;box-shadow:0 18px 44px rgba(27,27,31,.16),0 2px 6px rgba(27,27,31,.06);
transform-origin:top left;animation:dp-in .14s cubic-bezier(.2,.8,.2,1);}
@keyframes dp-in{from{opacity:0;transform:translateY(-4px) scale(.98);}to{opacity:1;transform:none;}}
@media(prefers-reduced-motion:reduce){.dp-pop{animation:none;}}
.dp-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}
.dp-title{font-weight:700;font-size:15px;letter-spacing:-.2px;padding-left:6px;}
.dp-nav{display:flex;gap:4px;}
.dp-nav button{width:32px;height:32px;display:grid;place-items:center;border:none;border-radius:8px;
background:transparent;color:var(--dark);cursor:pointer;transition:background-color .12s ease;}
.dp-nav button:hover{background:var(--bg);}
.dp-grid{display:grid;grid-template-columns:repeat(7,38px);justify-content:space-between;}
.dp-dow{height:28px;display:grid;place-items:center;font-size:11px;font-weight:600;
text-transform:uppercase;letter-spacing:.5px;color:var(--muted);}
.dp-day{width:38px;height:38px;display:grid;place-items:center;border:none;border-radius:999px;
background:transparent;color:var(--dark);font:500 14px/1 inherit;font-family:inherit;
font-variant-numeric:tabular-nums;cursor:pointer;transition:background-color .12s ease,color .12s ease;}
.dp-day:hover{background:var(--bg);}
.dp-day:focus-visible{outline:2px solid var(--primary);outline-offset:1px;}
.dp-day.out{color:#b9b9c4;}
.dp-day.today{box-shadow:inset 0 0 0 1.5px var(--primary);color:var(--primary);font-weight:700;}
.dp-day.sel,.dp-day.sel:hover{background:var(--primary);color:#fff;font-weight:700;box-shadow:none;}
.dp-day:disabled{color:#d3d3db;cursor:not-allowed;background:transparent;}
.dp-hint{font-size:12px;color:var(--muted);padding-right:6px;font-variant-numeric:tabular-nums;}
.dp-times{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;max-height:268px;overflow-y:auto;
padding:2px;margin:-2px;}
.dp-time{height:38px;border:1px solid var(--border);border-radius:10px;background:#fff;color:var(--dark);
font:600 13px/1 inherit;font-family:inherit;font-variant-numeric:tabular-nums;cursor:pointer;
transition:background-color .12s ease,border-color .12s ease,color .12s ease;}
.dp-time:hover{background:var(--bg);border-color:#c9c9d3;}
.dp-time:focus-visible{outline:2px solid var(--primary);outline-offset:1px;}
.dp-time.sel,.dp-time.sel:hover{background:var(--primary);border-color:var(--primary);color:#fff;}
.dp-time:disabled{color:#d3d3db;background:#fafafc;border-color:#efeff3;cursor:not-allowed;}
.dp-foot{display:flex;justify-content:flex-end;margin-top:10px;padding-top:10px;border-top:1px solid var(--border);}
.dp-foot button{border:none;background:transparent;color:var(--primary);font:600 13px/1 inherit;
font-family:inherit;padding:8px 10px;border-radius:8px;cursor:pointer;}
.dp-foot button:hover{background:rgba(196,30,46,.08);}
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
.profile-slot{margin-left:auto;position:relative;}
.profile{position:relative;}
.profile>summary{list-style:none;display:flex;align-items:center;gap:9px;padding:4px 10px 4px 4px;
border:1px solid var(--border);border-radius:999px;background:#fff;cursor:pointer;user-select:none;
transition:border-color .15s ease,box-shadow .15s ease;}
.profile>summary::-webkit-details-marker{display:none;}
.profile>summary:hover{border-color:#c9c9d3;}
.profile>summary:focus-visible,.profile[open]>summary{outline:none;border-color:var(--primary);
box-shadow:0 0 0 4px rgba(196,30,46,.14);}
.avatar{width:32px;height:32px;flex:none;display:grid;place-items:center;border-radius:999px;
background:var(--primary);color:#fff;font-size:13px;font-weight:700;letter-spacing:.3px;}
.avatar.lg{width:44px;height:44px;font-size:16px;}
.profile-name{font-size:14px;font-weight:600;}
.profile>summary svg{color:var(--muted);transition:transform .15s ease;}
.profile[open]>summary svg{transform:rotate(180deg);}
.profile-menu{position:absolute;right:0;top:calc(100% + 8px);z-index:40;width:272px;padding:8px;background:#fff;
border:1px solid var(--border);border-radius:16px;
box-shadow:0 18px 44px rgba(27,27,31,.16),0 2px 6px rgba(27,27,31,.06);
animation:dp-in .14s cubic-bezier(.2,.8,.2,1);}
.profile-head{display:flex;align-items:center;gap:12px;padding:10px 10px 12px;margin-bottom:6px;
border-bottom:1px solid var(--border);}
.profile-head .who{min-width:0;}
.profile-head .who-name{font-weight:700;font-size:15px;line-height:1.3;}
.profile-head .who-sub{font-size:12px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.role-tag{display:inline-block;margin-top:4px;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;
text-transform:uppercase;letter-spacing:.5px;background:var(--bg);color:var(--muted);}
.role-tag.staff{background:#fdecee;color:var(--primary);}
.menu-item{display:flex;align-items:center;gap:10px;width:100%;padding:9px 10px;border:none;border-radius:10px;
background:transparent;color:var(--dark);font:500 14px/1.3 inherit;font-family:inherit;text-align:left;cursor:pointer;}
.menu-item:hover,.menu-item:focus-visible{background:var(--bg);outline:none;}
.menu-item svg{flex:none;color:var(--muted);}
.menu-item.danger{color:var(--risk);} .menu-item.danger svg{color:var(--risk);}
.menu-sep{height:1px;background:var(--border);margin:6px 0;}
.auth-wrap{max-width:420px;margin:24px auto 0;}
.auth-wrap .btn-primary{width:100%;height:46px;margin-top:18px;font-size:15px;}
.auth-wrap .form-grid{grid-template-columns:1fr;}
.auth-note{margin-top:14px;font-size:13px;color:var(--muted);text-align:center;}
.rules{margin:6px 0 0;padding-left:18px;font-size:13px;color:var(--muted);columns:2;}
.detail-list{display:grid;grid-template-columns:180px 1fr;gap:0;margin:0;}
.detail-list dt{padding:12px 0;border-bottom:1px solid var(--border);color:var(--muted);font-size:13px;font-weight:600;}
.detail-list dd{padding:12px 0;margin:0;border-bottom:1px solid var(--border);font-size:15px;}
.detail-list dt:last-of-type,.detail-list dd:last-of-type{border-bottom:none;}
@media(max-width:600px){.profile-name{display:none}.detail-list{grid-template-columns:1fr}
.detail-list dt{border-bottom:none;padding-bottom:0}.rules{columns:1}}
@media(max-width:768px){.chart-bar{gap:8px}.bar-label{font-size:10px}.page-header h1{font-size:24px}}
"""

# ---------------- Date and time pickers (small progressive enhancement) ----------------
# Any <input type="date"> or <input type="time"> inside a .field is upgraded to
# a styled pop-up. Without JavaScript the browser's native inputs still work.
PICKER_JS = r"""
(function () {
  var MONTHS = ['January','February','March','April','May','June','July',
                'August','September','October','November','December'];
  var DOW = ['Mo','Tu','We','Th','Fr','Sa','Su'];
  var SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';
  var CAL = SVG + '<rect x="3" y="4" width="18" height="18" rx="3"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>';
  var CLOCK = SVG + '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>';
  var PREV = SVG.replace('"18" height="18"', '"16" height="16"') + '<path d="m15 18-6-6 6-6"/></svg>';
  var NEXT = SVG.replace('"18" height="18"', '"16" height="16"') + '<path d="m9 18 6-6-6-6"/></svg>';

  function iso(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function parse(s) {
    var p = s.split('-').map(Number);
    return new Date(p[0], p[1] - 1, p[2]);
  }
  function pretty(d) {
    return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  }
  function mins(t) { var p = t.split(':').map(Number); return p[0] * 60 + p[1]; }
  function hhmm(m) { return String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0'); }
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    if (tag === 'button') e.type = 'button';
    return e;
  }

  // Shared shell: swaps the input for a trigger button plus a floating pop-up.
  // describe() -> text shown on the trigger; paint(api) fills the pop-up.
  function attach(input, icon, describe, paint, beforeOpen) {
    var labelText = (input.labels && input.labels[0]) ? input.labels[0].textContent : 'Value';
    input.type = 'hidden';
    var wrap = el('div', 'dp');
    var btn = el('button', 'dp-trigger');
    btn.setAttribute('aria-haspopup', 'dialog');
    btn.setAttribute('aria-expanded', 'false');
    var pop = el('div', 'dp-pop');
    pop.setAttribute('role', 'dialog');
    pop.setAttribute('aria-label', 'Choose ' + labelText.toLowerCase());
    pop.hidden = true;
    input.after(wrap);
    wrap.append(btn, pop);

    function paintTrigger() {
      btn.innerHTML = '<span>' + describe() + '</span>' + icon;
      btn.setAttribute('aria-label', labelText + ': ' + describe());
    }
    function place() {
      var r = btn.getBoundingClientRect();
      var w = pop.offsetWidth, h = pop.offsetHeight;
      var left = Math.min(r.left, window.innerWidth - w - 12);
      var top = r.bottom + 8;
      if (top + h > window.innerHeight - 12) {
        top = (r.top - h - 8 > 12) ? r.top - h - 8 : Math.max(12, window.innerHeight - h - 12);
      }
      pop.style.left = Math.max(12, left) + 'px';
      pop.style.top = top + 'px';
    }
    function close() {
      pop.hidden = true;
      btn.setAttribute('aria-expanded', 'false');
    }
    function open() {
      if (beforeOpen) beforeOpen();
      paint(api);
      pop.hidden = false;
      btn.setAttribute('aria-expanded', 'true');
      place();
      var s = pop.querySelector('.sel') || pop.querySelector('.today') || pop.querySelector('button:not(:disabled)');
      if (s) { s.focus({ preventScroll: true }); s.scrollIntoView({ block: 'nearest' }); }
    }
    var api = {
      pop: pop, label: labelText, place: place,
      commit: function (value) {
        input.value = value;
        input.dispatchEvent(new Event('change', { bubbles: true }));
        paintTrigger();
        close();
        btn.focus();
      }
    };

    btn.onclick = function () { pop.hidden ? open() : close(); };
    document.addEventListener('mousedown', function (e) {
      if (!pop.hidden && !wrap.contains(e.target)) close();
    });
    wrap.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !pop.hidden) { close(); btn.focus(); }
    });
    window.addEventListener('scroll', function (e) {
      if (!pop.hidden && !pop.contains(e.target)) place();
    }, true);
    window.addEventListener('resize', function () { if (!pop.hidden) place(); });
    input.addEventListener('change', paintTrigger);
    paintTrigger();
  }

  function enhanceDate(input) {
    var min = input.min ? parse(input.min) : null;
    var today = new Date(); today.setHours(0, 0, 0, 0);
    var view;
    function sel() { return input.value ? parse(input.value) : today; }

    function paint(api) {
      var pop = api.pop, chosen = sel();
      pop.innerHTML = '';
      var head = el('div', 'dp-head');
      head.append(el('div', 'dp-title', MONTHS[view.getMonth()] + ' ' + view.getFullYear()));
      var nav = el('div', 'dp-nav');
      var prev = el('button', '', PREV); prev.setAttribute('aria-label', 'Previous month');
      var next = el('button', '', NEXT); next.setAttribute('aria-label', 'Next month');
      prev.onclick = function () { view = new Date(view.getFullYear(), view.getMonth() - 1, 1); paint(api); api.place(); };
      next.onclick = function () { view = new Date(view.getFullYear(), view.getMonth() + 1, 1); paint(api); api.place(); };
      nav.append(prev, next); head.append(nav); pop.append(head);

      var grid = el('div', 'dp-grid');
      DOW.forEach(function (d) { grid.append(el('div', 'dp-dow', d)); });
      var offset = (view.getDay() + 6) % 7;                 // Monday first
      var start = new Date(view.getFullYear(), view.getMonth(), 1 - offset);
      var daysInMonth = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
      var cells = Math.ceil((offset + daysInMonth) / 7) * 7;   // only the weeks this month needs
      for (var i = 0; i < cells; i++) {
        var d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
        var cls = 'dp-day';
        if (d.getMonth() !== view.getMonth()) cls += ' out';
        if (iso(d) === iso(today)) cls += ' today';
        if (iso(d) === iso(chosen)) cls += ' sel';
        var b = el('button', cls, String(d.getDate()));
        b.dataset.date = iso(d);
        b.setAttribute('aria-label', pretty(d));
        if (min && d < min) b.disabled = true;
        grid.append(b);
      }
      grid.onclick = function (e) {
        var t = e.target.closest('.dp-day');
        if (t && !t.disabled) api.commit(t.dataset.date);
      };
      pop.append(grid);

      var foot = el('div', 'dp-foot');
      var tb = el('button', '', 'Today');
      tb.onclick = function () { api.commit(iso(today)); };
      foot.append(tb); pop.append(foot);
    }

    attach(input, CAL, function () { return pretty(sel()); }, paint, function () {
      var c = sel();
      view = new Date(c.getFullYear(), c.getMonth(), 1);
    });
  }

  function enhanceTime(input) {
    var lo = input.min ? mins(input.min) : 0;
    var hi = input.max ? mins(input.max) : 23 * 60 + 30;
    var step = input.step ? Math.max(5, Math.round(Number(input.step) / 60)) : 30;
    // data-after="other_field_id": times at or before that field's value are unavailable
    var after = input.dataset.after ? document.getElementById(input.dataset.after) : null;

    function paint(api) {
      var pop = api.pop;
      pop.innerHTML = '';
      var head = el('div', 'dp-head');
      head.append(el('div', 'dp-title', api.label));
      head.append(el('div', 'dp-hint', hhmm(lo) + ' to ' + hhmm(hi)));
      pop.append(head);
      var grid = el('div', 'dp-times');
      var floor = (after && after.value) ? mins(after.value) : -1;
      for (var m = lo; m <= hi; m += step) {
        var t = hhmm(m);
        var b = el('button', 'dp-time' + (t === input.value ? ' sel' : ''), t);
        b.dataset.time = t;
        if (m <= floor) b.disabled = true;
        grid.append(b);
      }
      grid.onclick = function (e) {
        var t = e.target.closest('.dp-time');
        if (t && !t.disabled) api.commit(t.dataset.time);
      };
      pop.append(grid);
    }

    attach(input, CLOCK, function () { return input.value || 'Select time'; }, paint);

    // Keep the pair valid: if the earlier field moves past this one, push this one on.
    if (after) {
      after.addEventListener('change', function () {
        if (input.value && after.value && mins(input.value) <= mins(after.value)) {
          var next = Math.min(mins(after.value) + 2 * step, hi);
          if (next <= mins(after.value)) next = hi;
          input.value = hhmm(next);
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.field input[type=date]').forEach(enhanceDate);
    document.querySelectorAll('.field input[type=time]').forEach(enhanceTime);
  });
})();
"""

# ---------------- Profile menu ----------------
# Closes the profile drop-down when you click elsewhere or press Escape.
MENU_JS = r"""
document.addEventListener('click', function (e) {
  document.querySelectorAll('details.profile[open]').forEach(function (d) {
    if (!d.contains(e.target)) d.removeAttribute('open');
  });
});
document.addEventListener('keydown', function (e) {
  if (e.key !== 'Escape') return;
  document.querySelectorAll('details.profile[open]').forEach(function (d) {
    d.removeAttribute('open');
    d.querySelector('summary').focus();
  });
});
"""


def _icon(path, size=18):
    return NotStr(
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>'
    )


ICON_CHEVRON = '<path d="m6 9 6 6 6-6"/>'
ICON_CALENDAR = '<rect x="3" y="4" width="18" height="18" rx="3"/><path d="M16 2v4M8 2v4M3 10h18"/>'
ICON_USER = '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'
ICON_KEY = '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M17 6l3 3M14 9l2 2"/>'
ICON_SIGN_OUT = '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>'


def initials(user):
    return ((user.get("first_name") or "?")[:1] + (user.get("last_name") or "")[:1]).upper()


def ProfileMenu(user):
    """Top-right corner: a 'Sign in' button for visitors, or the signed-in
    person's avatar and name with a drop-down menu."""
    if not user:
        return Div(A("Sign in", href="/signin", cls="btn btn-primary btn-sm"), cls="profile-slot")
    full_name = f'{user["first_name"]} {user["last_name"]}'
    return Div(
        Details(
            Summary(
                Span(initials(user), cls="avatar"),
                Span(user["first_name"], cls="profile-name"),
                _icon(ICON_CHEVRON, 16),
                aria_label=f"Account menu for {full_name}",
            ),
            Div(
                Div(
                    Span(initials(user), cls="avatar lg"),
                    Div(
                        Div(full_name, cls="who-name"),
                        Div(user["email"], cls="who-sub"),
                        Span(user["role"].title(), cls=f'role-tag {user["role"]}'),
                        cls="who",
                    ),
                    cls="profile-head",
                ),
                A(_icon(ICON_CALENDAR), "My bookings", href="/bookings", cls="menu-item"),
                A(_icon(ICON_USER), "Account", href="/account", cls="menu-item"),
                A(_icon(ICON_KEY), "Change password", href="/account/password", cls="menu-item"),
                Div(cls="menu-sep"),
                Form(Button(_icon(ICON_SIGN_OUT), "Sign out", cls="menu-item danger"),
                     method="post", action="/signout"),
                cls="profile-menu",
            ),
            cls="profile",
        ),
        cls="profile-slot",
    )


# ---------------- Basic components ----------------
def Alert(message, kind="info"):
    if not message:
        return None
    if kind not in ("info", "ok", "warn", "error"):
        kind = "info"      # never trust a style name taken from the address bar
    return Div(message, cls=f"alert {kind}")


def Empty(title, message="", icon="🗂️"):
    return Div(Span(icon, cls="icon"), H4(title), P(message, cls="muted"), cls="empty")


def Card(title, *content, hint=None, flush=False):
    return Div(
        Div(H3(title), Span(hint, cls="card-hint") if hint else None, cls="card-head"),
        Div(*content, cls="card-body flush" if flush else "card-body"),
        cls="card",
    )


def StatItem(icon, value, unit="", label="", note="", tone=""):
    return Div(
        Span(icon, cls="icon"),
        P(f"{value}{unit}", cls="number"),
        P(label, cls="label"),
        P(note, cls="note") if note else None,
        cls=f"stat {tone}".strip(),
    )


def StatsRow(*items):
    return Div(*items, cls="stats-row")


def StatusBadge(status):
    return Span(status.replace("_", " ").title(), cls=f"badge {status}")


def Cell(main, sub=""):
    return Td(Div(main, cls="cell-main"), Div(sub, cls="cell-sub") if sub else None)


def DataTable(headers, rows, empty_msg="No data to show yet."):
    if not rows:
        return Empty("Nothing here yet", empty_msg)
    return Div(Table(Thead(Tr(*[Th(h) for h in headers])), Tbody(*rows)), cls="table-wrap")


def Field(name, value="", help_text="", type="text", label=None, **attrs):
    return Div(
        Label(label or name.replace("_", " ").title(), _for=name),
        Input(name=name, id=name, value=str(value), type=type, **attrs),
        Div(help_text, cls="help") if help_text else None,
        cls="field",
    )


def SelectField(name, options, value="", blank="", label=None):
    opts = []
    if blank:
        opts.append(Option(blank, value="", selected=(value == "")))
    for o in options:
        val, txt = (o, o) if not isinstance(o, (list, tuple)) else (o[0], o[1])
        opts.append(Option(txt, value=str(val), selected=(str(value) == str(val))))
    return Div(
        Label(label or name.replace("_", " ").title(), _for=name),
        Select(*opts, name=name, id=name),
        cls="field",
    )


def TextArea_(name, value="", full=True):
    return Div(
        Label(name.replace("_", " ").title(), _for=name),
        Textarea(value, name=name, id=name, rows=3),
        cls="field full" if full else "field",
    )


def ListingCard(icon, title, meta, body, price="", action=None):
    return Div(
        Span(icon, cls="icon"), H4(title), Div(meta, cls="meta"),
        P(body, cls="body"),
        Div(price, cls="price") if price else None,
        action,
        cls="listing",
    )


def DetailList(pairs):
    """A two-column list of label / value pairs."""
    items = []
    for label, value in pairs:
        items += [Dt(label), Dd(value if value not in (None, "") else "Not set")]
    return Dl(*items, cls="detail-list")


# ---------------- Charts (dependency-free: CSS/SVG, no JS, no CDN) ----------------
def _pairs(data, label_key="label", value_key="value"):
    if not data:
        return []
    rows = []
    for row in data:
        if isinstance(row, dict):
            label, value = row.get(label_key, ""), row.get(value_key, 0)
        else:
            label, value = row[0], row[1]
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
    bars = [
        Div(
            Div(Span(f"{v:g}{unit}", cls="bar-value"), cls="bar-fill",
                style=f"height:{max((v / peak) * 100, 2):.1f}%"),
            Div(lbl, cls="bar-label"),
            cls="bar-col",
        )
        for lbl, v in rows
    ]
    return Div(*bars, cls="chart chart-bar")


def LineChart(data, unit="", height=220, width=720, label_key="label", value_key="value"):
    rows = _pairs(data, label_key, value_key)
    if not rows:
        return Div("No data for this period.", cls="chart-empty")
    pad_x, pad_y = 36, 18
    peak = max((v for _, v in rows), default=0) or 1.0
    span = max(len(rows) - 1, 1)
    plot_w, plot_h = width - pad_x * 2, height - pad_y * 2

    pts, dots, labels = [], [], []
    for i, (lbl, v) in enumerate(rows):
        x = pad_x + (i / span) * plot_w
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


# ---------------- Page shell ----------------
def Page(title, *content, subtitle=None, active="/", actions=None, user=None):
    """The page frame. `user` is the signed-in person (or None): it decides
    which navigation links show and what the top-right corner looks like."""
    role = user["role"] if user else None
    visible_nav = [n for n in NAV if user and (n[2] == "all" or role == "staff")]
    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(f"{title} | Campus Booking"),
            Style(CSS),
            Script(PICKER_JS),
            Script(MENU_JS),
        ),
        Body(
            Header(
                Div(
                    A("Campus Booking", href="/", cls="brand"),
                    Nav(*[A(label, href=path, cls="nav-link active" if active == path else "nav-link")
                          for path, label, _ in visible_nav]),
                    ProfileMenu(user),
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
            Main(Div(*content, cls="section-wrap"), cls="section-padding"),
            Footer(Div(P("Campus Resource Booking — FastHTML + Supabase prototype"), cls="section-wrap"), cls="site-footer"),
        )
    )