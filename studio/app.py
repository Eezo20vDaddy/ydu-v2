"""Local catalog studio. Bind localhost only. Does not call live Zoho or ydu.com.au."""

from __future__ import annotations

import cgi
import json
import re
import traceback
import urllib.error
from html import escape, unescape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from studio import ai, ebay, seo, store, woo

HOST = "127.0.0.1"
PORT = 8877

_PROMPT_SCRIPT = """<script>
(function () {
  var openBtn = document.getElementById("assistant-prompt-open");
  var dialog = document.getElementById("assistant-prompt-dialog");
  var closeBtn = document.getElementById("assistant-prompt-close");
  if (!openBtn || !dialog || !closeBtn) return;
  var tabs = Array.prototype.slice.call(dialog.querySelectorAll("[data-prompt-tab]"));
  function select(id, focusTab) {
    tabs.forEach(function (tab) {
      tab.setAttribute("aria-selected", tab.getAttribute("data-prompt-tab") === id ? "true" : "false");
    });
    dialog.querySelectorAll("[data-prompt-panel]").forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-prompt-panel") !== id;
    });
    if (!focusTab) return;
    var next = dialog.querySelector('[data-prompt-tab="' + id + '"]');
    if (next) next.focus();
  }
  openBtn.addEventListener("click", function () {
    if (typeof dialog.showModal === "function") dialog.showModal();
  });
  closeBtn.addEventListener("click", function () { dialog.close(); });
  tabs.forEach(function (tab, index) {
    tab.addEventListener("click", function () {
      select(tab.getAttribute("data-prompt-tab"), false);
    });
    tab.addEventListener("keydown", function (event) {
      var next = null;
      if (event.key === "ArrowRight") next = tabs[(index + 1) % tabs.length];
      else if (event.key === "ArrowLeft") next = tabs[(index - 1 + tabs.length) % tabs.length];
      else if (event.key === "Home") next = tabs[0];
      else if (event.key === "End") next = tabs[tabs.length - 1];
      else return;
      event.preventDefault();
      select(next.getAttribute("data-prompt-tab"), true);
    });
  });
})();
</script>"""


def _prompt_editor() -> str:
    tabs: list[str] = []
    panels: list[str] = []
    for index, spec in enumerate(ai.PROMPTS):
        key = escape(spec["key"])
        label = escape(spec["label"])
        selected = "true" if index == 0 else "false"
        tabs.append(
            f'<button type="button" class="prompt-tab" role="tab" id="prompt-tab-{key}" '
            f'data-prompt-tab="{key}" aria-controls="prompt-panel-{key}" aria-selected="{selected}">{label}</button>'
        )
        hidden = "" if index == 0 else " hidden"
        panels.append(
            f'<div role="tabpanel" id="prompt-panel-{key}" data-prompt-panel="{key}" '
            f'aria-labelledby="prompt-tab-{key}"{hidden}>'
            f'<form method="post" action="/assistant-prompt">'
            f'<input type="hidden" name="key" value="{key}">'
            f'<textarea name="prompt" rows="16" aria-label="{label} prompt">{escape(ai.prompt_text(spec["key"]))}</textarea>'
            f'<p class="muted">{escape(spec["note"])}</p>'
            f'<p class="muted prompt-usage">{escape(spec["usage"])}</p>'
            f'<div class="bar">'
            f'<button type="submit" name="op" value="save">Save</button>'
            f'<button type="submit" name="op" value="reset">Reset</button>'
            f"</div></form></div>"
        )
    return (
        '<div class="prompt-tabs" role="tablist" aria-label="Prompts sent to the assistant">'
        + "".join(tabs)
        + "</div>"
        + "".join(panels)
    )


def page(title: str, body: str) -> bytes:
    editor = _prompt_editor()
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
  :root {{ --navy:#1B3A4B; --blue:#4A90E2; --bg:#f4f7fb; --line:#dde6f0; --warn:#b46900; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:15px/1.45 "Segoe UI", sans-serif; background:var(--bg); color:#1c2733; }}
  header {{ background:var(--navy); color:#fff; padding:12px 20px; display:flex; gap:18px; align-items:center; }}
  header a {{ color:#fff; }}
  main {{ padding:16px 20px 40px; }}
  .grid {{ display:grid; grid-template-columns: 20vw minmax(0, 1fr) 30vw; gap:12px; width:100%; }}
  .grid > .card {{ min-width:0; }}
  .card {{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:12px; }}
  h1 {{ font-size:18px; margin:0 0 8px; }}
  h2 {{ font-size:14px; margin:0 0 8px; color:var(--navy); }}
  label {{ display:block; font-size:12px; color:#5b6b7a; margin-top:8px; }}
  input, select, textarea {{ width:100%; padding:6px 8px; border:1px solid var(--line); border-radius:6px; }}
  button, .btn {{ background:var(--navy); color:#fff; border:0; border-radius:6px; padding:7px 10px; cursor:pointer; }}
  .warn {{ background:#fbf1de; border-left:4px solid var(--warn); padding:8px; }}
  .new {{ background:#fdecea; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ border-bottom:1px solid var(--line); text-align:left; vertical-align:top; padding:4px; }}
  .evidence {{ min-width:0; max-width:100%; }}
  .evidence table {{ table-layout:fixed; width:100%; }}
  .evidence th, .evidence td {{ overflow-wrap:break-word; }}
  .term-counts {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:8px; margin:0 0 10px; min-width:0; max-width:100%; }}
  .term-counts button {{ display:block; width:100%; min-width:0; border:1px solid var(--line); border-radius:8px; padding:6px 8px; background:#f7f9fc; text-align:left; font:inherit; color:inherit; cursor:pointer; }}
  .term-counts button.is-zero {{ cursor:default; }}
  .term-counts button:hover:not(.is-zero) {{ border-color:var(--blue); }}
  .term-counts button:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px; }}
  .term-counts button.is-active {{ background:#e8f3fc; border-color:var(--blue); box-shadow:inset 0 0 0 1px var(--blue); }}
  .term-counts strong {{ display:block; font-size:18px; line-height:1.1; color:var(--navy); }}
  .term-counts span {{ display:block; font-size:12px; color:#5b6b7a; overflow-wrap:anywhere; }}
  .fitment col.y {{ width:6%; }}
  .fitment col.mk {{ width:12%; }}
  .fitment col.md {{ width:10%; }}
  .fitment col.sub {{ width:21%; }}
  .fitment col.var {{ width:18%; }}
  .fitment col.eng {{ width:12%; }}
  .fitment col.st {{ width:8%; }}
  .fitment col.act {{ width:13%; }}
  .fitment td.long {{ overflow-wrap:break-word; }}
  .fitment td.act {{ overflow-wrap:normal; white-space:nowrap; }}
  .fitment td.act form {{ display:inline-block; margin:0; vertical-align:middle; }}
  .fitment td.act form + form {{ margin-left:4px; }}
  .fitment td.act button {{ width:24px; height:24px; padding:0; display:inline-flex; align-items:center; justify-content:center; line-height:0; vertical-align:middle; }}
  .fitment td.act button svg {{ display:block; }}
  .fitment td.act button:hover {{ background:var(--blue); }}
  .fitment td.act button:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px; }}
  .fitment tr.filters th {{ font-weight:400; padding:2px 4px 6px; }}
  .fitment .col-filter {{ display:block; width:100%; min-width:0; max-width:100%; margin:0; padding:3px 4px; font:12px/1.3 "Segoe UI", sans-serif; }}
  .replace-col {{ display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin:0 0 8px; min-width:0; max-width:100%; }}
  .replace-col select, .replace-col input {{ width:auto; flex:1 1 6.5rem; min-width:0; max-width:100%; height:32px; margin:0; }}
  .replace-col select {{ flex:0 1 9.5rem; }}
  .replace-col button {{ width:auto; flex:0 0 auto; height:32px; padding:0 12px; white-space:nowrap; }}
  .replace-col select:focus-visible,
  .replace-col input:focus-visible,
  .replace-col button:focus-visible,
  #replace-summary button:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px; }}
  .fitment td.fit-hit {{ background:#e8f3fc; box-shadow:inset 0 0 0 2px var(--blue); }}
  #replace-summary {{ width:fit-content; height:fit-content; max-width:min(28rem, calc(100vw - 32px)); max-height:none; margin:auto; background:#fff; }}
  #replace-summary p {{ margin:0 0 12px; color:var(--navy); }}
  #replace-summary .bar {{ margin:0; justify-content:flex-end; }}
  #replace-summary button {{ width:auto; }}
  #replace-summary button:hover {{ background:var(--blue); }}
  #replace-summary:not([open]) {{ display:none; }}
  .nums col.num {{ width:18%; }}
  .nums col.brand {{ width:12%; }}
  .nums col.src {{ width:10%; }}
  .nums col.link {{ width:40%; }}
  .nums col.tick {{ width:8%; }}
  .nums col.act {{ width:12%; }}
  .nums td.link {{ max-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; overflow-wrap:normal; }}
  .film img {{ height:72px; margin:4px; border:2px solid transparent; }}
  .film .hero {{ border-color:var(--blue); }}
  .film .shot {{ margin:0 0 8px; }}
  .film .shot-open {{ padding:0; background:none; border:2px solid transparent; border-radius:6px; cursor:zoom-in; line-height:0; display:inline-block; }}
  .film .shot-open.hero {{ border-color:var(--blue); }}
  .film .shot-open img {{ cursor:zoom-in; }}
  .film .shot-open:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px; }}
  .film .shot-actions {{ display:flex; flex-wrap:nowrap; gap:6px; align-items:center; margin-top:4px; max-width:100%; }}
  .film .shot-actions form {{ margin:0; flex:0 0 auto; }}
  .film .shot-actions button {{ width:auto; margin:0; padding:4px 8px; font-size:12px; line-height:1.2; white-space:nowrap; }}
  .film .shot-actions button:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px; }}
  .film > form.bar > button {{ height:34px; width:34px; flex:0 0 34px; padding:0; display:inline-flex; align-items:center; justify-content:center; line-height:0; }}
  .listing-pictures {{ margin:0 0 12px; }}
  .candidates {{ display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 0; }}
  .candidates label {{ display:flex; flex-direction:column; align-items:flex-start; gap:4px; width:104px; margin:0; color:inherit; }}
  .candidates input {{ width:auto; height:auto; margin:0; }}
  .candidates img {{ width:96px; height:72px; margin:0; object-fit:contain; background:#f7f9fc; border:1px solid var(--line); border-radius:6px; }}
  .listing-pictures .bar button {{ width:auto; }}
  .bar {{ display:flex; gap:8px; align-items:center; margin-top:8px; }}
  .paste {{ display:flex; gap:8px; align-items:stretch; margin:0 0 12px; }}
  .paste input {{ flex:1; width:auto; height:34px; margin:0; }}
  .paste button {{ height:34px; width:auto; padding:0 14px; font:inherit; line-height:1; white-space:nowrap; }}
  .alias {{ align-items:stretch; }}
  .alias input:not([type=hidden]) {{ height:34px; width:auto; flex:1; min-width:0; }}
  .alias button {{ height:34px; width:auto; flex:0 0 auto; padding:0 14px; font:inherit; line-height:1; white-space:nowrap; }}
  .reread {{ margin-top:12px; }}
  .reread button {{ width:auto; }}
  .catalog-head {{ display:flex; justify-content:space-between; align-items:center; gap:12px; margin:0 0 12px; }}
  .catalog-head h1 {{ margin:0; flex:0 0 auto; }}
  .catalog-note {{ display:flex; align-items:center; justify-content:flex-end; gap:12px; min-width:0; }}
  .catalog-head p {{ margin:0; text-align:right; min-width:0; }}
  .catalog-cascade {{ margin:0; flex:0 0 auto; color:var(--navy); font-size:13px; font-weight:600; white-space:nowrap; }}
  .catalog-cascade input:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px; }}
  .cascade {{ display:grid; grid-template-columns:repeat(6, minmax(0, 1fr)); gap:12px; align-items:start; }}
  .cascade .card-head {{ display:flex; justify-content:space-between; align-items:baseline; gap:8px; margin:0 0 8px; }}
  .cascade .card-head h2 {{ margin:0; }}
  .cascade-search {{ margin:0 0 8px; font-size:13px; padding:5px 8px; width:100%; }}
  .choices {{ max-height:70vh; overflow:auto; display:flex; flex-direction:column; gap:2px; }}
  .choices label.cascade-hidden {{ display:none; }}
  .choices label {{ display:flex; align-items:flex-start; gap:6px; margin:0; color:inherit; font-size:13px; }}
  .choices input {{ width:auto; height:auto; margin:2px 0 0; flex:0 0 auto; }}
  .addpath {{ display:grid; grid-template-columns:repeat(6, minmax(0, 1fr)) auto; gap:8px; align-items:end; margin-top:12px; }}
  .addpath label {{ margin:0; }}
  .addpath button {{ width:auto; height:34px; padding:0 14px; }}
  label.check {{ display:flex; align-items:center; gap:8px; }}
  label.check input {{ width:auto; height:auto; margin:0; flex:0 0 auto; }}
  .muted {{ color:#5b6b7a; font-size:12px; }}
  .mapper .sample {{ font-size:13px; word-break:break-word; }}
  .map-row {{ padding:8px 0; border-bottom:1px solid var(--line); }}
  .map-head {{ font-weight:600; color:var(--navy); }}
  .map-controls {{ display:grid; grid-template-columns: 1fr 1fr; gap:8px; align-items:end; margin-top:4px; }}
  .map-controls select {{ width:100%; }}
  .chat {{ margin-top:12px; }}
  .thread {{ max-height:280px; overflow:auto; display:flex; flex-direction:column; gap:8px; padding:4px 0 8px; }}
  .bubble {{ max-width:78%; padding:8px 10px; border-radius:10px; white-space:pre-wrap; }}
  .bubble.user {{ align-self:flex-end; background:#e7f0fa; }}
  .bubble.assistant {{ align-self:flex-start; background:#f7f9fc; border:1px solid var(--line); }}
  .bubble a {{ color:var(--navy); overflow-wrap:anywhere; }}
  .part-line {{ display:flex; gap:6px; align-items:center; }}
  .part-line input {{ flex:1 1 auto; width:auto; min-width:0; margin:0; }}
  button.icon {{ width:34px; height:34px; padding:0; flex:0 0 auto; display:inline-flex; align-items:center; justify-content:center; }}
  button.icon:hover {{ background:var(--blue); }}
  button.icon:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px; }}
  .bubble.assistant.error {{ background:#fbf1de; border-color:var(--warn); }}
  .bubble img.chat-shot {{ display:block; width:140px; height:96px; max-width:100%; margin-top:6px; object-fit:contain; background:#fff; border:1px solid var(--line); border-radius:6px; }}
  .thread-wait {{ display:flex; align-items:center; gap:8px; align-self:flex-start; min-height:28px; color:#5b6b7a; font-size:13px; }}
  .thread-wait .spin {{ width:14px; height:14px; box-sizing:border-box; border:2px solid var(--line); border-top-color:var(--blue); border-radius:50%; animation:chat-spin .7s linear infinite; flex:0 0 auto; }}
  @keyframes chat-spin {{ to {{ transform:rotate(360deg); }} }}
  @media (prefers-reduced-motion: reduce) {{
    .thread-wait .spin {{ animation:none; }}
  }}
  .chat-previews {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }}
  .chat-previews:empty {{ display:none; margin:0; }}
  .chat-previews img {{ width:72px; height:54px; object-fit:contain; background:#f7f9fc; border:1px solid var(--line); border-radius:6px; }}
  .chat .compose {{ display:flex; gap:8px; align-items:flex-end; margin-top:8px; }}
  .chat .compose textarea {{ flex:1 1 auto; width:auto; min-width:0; margin:0; resize:vertical; }}
  .chat textarea.drop {{ outline:2px solid var(--blue); outline-offset:2px; }}
  .chat .compose textarea:focus-visible, .chat .compose button.icon:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px; }}
  .bubble {{ overflow-wrap:anywhere; }}
  .linkcard {{ display:flex; gap:8px; align-items:flex-start; border:1px solid var(--line); border-radius:8px; padding:6px; margin:6px 0; }}
  .linkcard img, .nophoto {{ width:56px; height:56px; object-fit:contain; background:#f7f9fc; border-radius:6px; flex:0 0 56px; }}
  .nophoto {{ display:flex; align-items:center; justify-content:center; font-size:10px; color:#5b6b7a; text-align:center; }}
  .linkcard button {{ width:auto; margin:4px 4px 0 0; padding:4px 8px; font-size:12px; }}
  .linkcard form {{ display:inline; }}
  .editrow {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
  .editrow h2 {{ margin:0; }}
  .editrow button {{ width:auto; }}
  .editrow .bar {{ margin-top:0; }}
  #link-edit .linkcard img, #link-edit .nophoto {{ width:140px; height:140px; object-fit:contain; flex:0 0 140px; }}
  dialog {{ border:0; border-radius:12px; padding:16px; width:80vw; max-width:80vw; max-height:85vh; overflow:auto; }}
  dialog::backdrop {{ background:rgba(27, 58, 75, 0.45); }}
  #photo-view:not([open]) {{ display:none; }}
  #photo-view[open] {{ width:90vw; max-width:90vw; height:90vh; max-height:90vh; margin:auto; padding:12px; display:grid; grid-template-rows:minmax(0, 1fr) auto; gap:12px; overflow:hidden; background:#fff; }}
  #photo-view::backdrop {{ background:rgba(8, 12, 16, 0.88); }}
  #photo-view img {{ width:100%; height:100%; max-width:100%; max-height:100%; margin:0; border:0; object-fit:contain; background:#fff; }}
  #photo-view .bar {{ margin:0; justify-content:flex-end; flex-wrap:wrap; }}
  #photo-view .pager {{ display:flex; gap:8px; margin-right:auto; }}
  #photo-view form:not([hidden]) {{ display:flex; margin:0; }}
  #photo-view [hidden] {{ display:none; }}
  #photo-view button {{ width:auto; }}
  #photo-view button:hover {{ background:var(--blue); }}
  #photo-view button:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px; }}
  #photo-view .muted {{ margin:0; align-self:center; }}
  #photo-hover {{ position:fixed; z-index:40; box-sizing:border-box; width:min(480px, calc(100vw - 16px)); height:min(480px, calc(100vh - 16px)); padding:8px; background:#fff; border:1px solid var(--line); border-radius:10px; box-shadow:0 12px 36px rgba(8, 12, 16, 0.28); pointer-events:none; }}
  #photo-hover[hidden] {{ display:none; }}
  #photo-hover img {{ display:block; width:100%; height:100%; margin:0; border:0; object-fit:contain; background:#fff; }}
  header .menu-btn {{ margin-left:auto; width:auto; background:transparent; color:#fff; border:1px solid #fff; white-space:nowrap; }}
  header .menu-btn:hover, header .menu-btn:focus-visible {{ background:var(--blue); }}
  header .menu-btn:focus-visible {{ outline:2px solid #fff; outline-offset:2px; }}
  #assistant-prompt-dialog:not([open]) {{ display:none; }}
  #assistant-prompt-dialog textarea {{ min-height:34vh; font:13px/1.45 "Segoe UI", sans-serif; }}
  #assistant-prompt-dialog .bar button {{ width:auto; }}
  #assistant-prompt-dialog .bar button:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px; }}
  #assistant-prompt-dialog .prompt-head {{ display:flex; justify-content:space-between; align-items:center; gap:12px; margin:0 0 10px; }}
  #assistant-prompt-dialog .prompt-head h2 {{ margin:0; }}
  #assistant-prompt-dialog .prompt-head button {{ width:auto; }}
  #assistant-prompt-dialog .prompt-tabs {{ display:flex; flex-wrap:wrap; gap:6px; margin:0 0 10px; }}
  #assistant-prompt-dialog .prompt-tab {{ width:auto; background:#f7f9fc; color:var(--navy); border:1px solid var(--line); }}
  #assistant-prompt-dialog .prompt-tab[aria-selected="true"] {{ background:var(--navy); color:#fff; border-color:var(--navy); }}
  #assistant-prompt-dialog .prompt-tab:hover {{ background:var(--blue); color:#fff; border-color:var(--blue); }}
  #assistant-prompt-dialog .prompt-tab[aria-selected="true"]:hover {{ background:var(--navy); border-color:var(--navy); }}
  #assistant-prompt-dialog .prompt-tab:focus-visible {{ outline:2px solid var(--blue); outline-offset:2px; }}
  #assistant-prompt-dialog [hidden] {{ display:none; }}
  #assistant-prompt-dialog .muted {{ margin:8px 0 0; }}
</style></head><body>
<header><strong>Catalog studio</strong>
  <a href="/">Part</a><a href="/catalog">Vehicle catalog</a><a href="/compare">Zoho / WordPress</a>
  <button type="button" class="menu-btn" id="assistant-prompt-open">Assistant prompt</button>
</header>
<main>{body}</main>
<dialog id="assistant-prompt-dialog" aria-labelledby="assistant-prompt-title">
  <div class="prompt-head">
    <h2 id="assistant-prompt-title">Assistant prompt</h2>
    <button type="button" id="assistant-prompt-close">Close</button>
  </div>
  {editor}
</dialog>
{_PROMPT_SCRIPT}
</body></html>"""
    return html.encode("utf-8")


def home(error: str = "", sku: str = "", name: str = "") -> bytes:
    rows = "".join(
        f"<tr><td><a href=\"/item?id={r['id']}\">{escape(r['canonical_sku'])}</a></td><td>{escape(r['name'] or '')}</td><td>{escape(r['status'])}</td></tr>"
        for r in store.list_items()
    )
    alert = f"<p class=\"warn\" role=\"alert\">{escape(error)}</p>" if error else ""
    body = f"""
    <h1>Parts</h1>
    <form method="post" action="/item/new" class="card" style="max-width:480px">
      {alert}
      <label>New SKU</label><input name="sku" value="{escape(sku)}" required>
      <label>Name</label><input name="name" value="{escape(name)}">
      <div class="bar"><button>Create</button></div>
    </form>
    <table><tr><th>SKU</th><th>Name</th><th>Status</th></tr>{rows}</table>
    """
    return page("Parts", body)


_MAP_CHOICES = (
    ("year", "Year"),
    ("make", "Make"),
    ("model", "Model"),
    ("submodel", "Submodel"),
    ("variant", "Variant"),
    ("engine_code", "Engine code"),
    ("skip", "Skip"),
)
_EXTRACT_CHOICES = (
    ("whole_cell", "Whole cell"),
    ("one_row_per_code", "One row per code"),
)


def _choice_select(name: str, choices: tuple, selected: str) -> str:
    options = []
    for value, label in choices:
        mark = " selected" if value == selected else ""
        options.append(f"<option value=\"{escape(value)}\"{mark}>{escape(label)}</option>")
    return f"<select name=\"{escape(name)}\">{''.join(options)}</select>"


def _remember_mapping(item_id: int, payload: dict) -> dict:
    cached = payload.get("assistant")
    if isinstance(cached, dict) and cached.get("openai") and cached.get("columns"):
        return cached
    result = ai.suggest_table_mapping(payload.get("headers") or [], payload.get("rows") or [])
    if not result.get("openai"):
        return result
    saved = {
        "openai": True,
        "model": result.get("model") or "",
        "note": result.get("note") or "",
        "columns": result.get("columns") or [],
        "model_columns": result.get("model_columns") or [],
    }
    blob = json.dumps(saved)
    if "sk-" in blob:
        return result
    payload["assistant"] = saved
    path = store.ROOT / "data" / "studio-media" / str(item_id) / "pending-table.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return saved


def _column_mapper(item_id: int) -> str:
    pending = store.ROOT / "data" / "studio-media" / str(item_id) / "pending-table.json"
    if not pending.exists():
        return ""
    payload = json.loads(pending.read_text(encoding="utf-8"))
    headers = list(payload.get("headers") or [])
    rows = list(payload.get("rows") or [])
    if not headers:
        return ""
    suggestion = _remember_mapping(item_id, payload)
    sample = rows[0] if rows else {}
    by_header = {
        str(col.get("header") or "").strip().lower(): col
        for col in suggestion.get("columns") or []
    }
    if suggestion.get("openai"):
        model = escape(suggestion.get("model") or "")
        who = f"The assistant ({model}) filled this mapping from the listing." if model else "The assistant filled this mapping from the listing."
        note_html = f"<p>{who} Check each column, then save. The mapping is stored for the next part with the same header.</p>"
    else:
        note = suggestion.get("note") or "The assistant did not run. Columns were filled from the header names."
        note_html = f"<p>{escape(note)}</p>"
    body_rows = []
    for i, header in enumerate(headers):
        col = by_header.get(header.strip().lower(), {})
        target = col.get("target") or "skip"
        if target not in store.MAP_FIELDS:
            target = "skip"
        extract = col.get("extract") or "whole_cell"
        if extract == "engine_codes_inside":
            extract = "one_row_per_code"
        cell = "" if sample.get(header) is None else str(sample.get(header))
        if cell.strip():
            sample_html = escape(cell)
        else:
            sample_html = "<span class='muted'>(empty)</span>"
        _text, codes, _clean = ebay.peel_engine_codes(cell)
        if len(codes) >= 2 and target in {"variant", "engine_code"}:
            extract = "one_row_per_code"
        if extract == "one_row_per_code":
            extract_html = _choice_select(f"extract_{i}", _EXTRACT_CHOICES, "one_row_per_code")
        else:
            extract_html = (
                f"<input type='hidden' name='extract_{i}' value='whole_cell'>"
                "<span class='muted'>Whole cell</span>"
            )
        body_rows.append(
            "<div class='map-row'>"
            f"<div class='map-head'>{escape(header)}</div>"
            f"<input type='hidden' name='header_{i}' value=\"{escape(header)}\">"
            f"<div class='sample'>{sample_html}</div>"
            f"<div class='map-controls'><div>{_choice_select(f'target_{i}', _MAP_CHOICES, target)}</div>"
            f"<div>{extract_html}</div></div>"
            "</div>"
        )
    return (
        "<div class='card warn' data-assistant='openai'>"
        if suggestion.get("openai")
        else "<div class='card warn' data-assistant='header'>"
    ) + (
        "<h2>New table version</h2>"
        f"{note_html}"
        f"<form method='post' action='/item/template'><input type='hidden' name='item_id' value='{item_id}'>"
        "<div class='mapper'>"
        + "".join(body_rows)
        + "</div><div class='bar'><button>Save template and extract</button></div></form></div>"
    )


_FRESH_ATTRS = (
    ("make", "data-new-make"),
    ("model", "data-new-model"),
    ("submodel", "data-new-submodel"),
    ("engine_code", "data-new-engine"),
)


def _fresh_flags(row, fresh: dict[str, set[str]]) -> str:
    """Mark a row when its stored name is one of the counted new catalog terms."""
    parts = []
    for level, attr in _FRESH_ATTRS:
        value = row[level] or ""
        if value in fresh.get(level, ()):
            parts.append(f' {attr}="1"')
    return "".join(parts)


def _term_count_box(attr: str, label: str, count: int) -> str:
    inactive = " is-zero" if count == 0 else ""
    guard = " aria-disabled='true'" if count == 0 else ""
    return (
        f"<button type='button' class='term-count{inactive}' data-term='{attr}' "
        f"data-count='{count}' aria-pressed='false'{guard}>"
        f"<strong>{count}</strong><span>{escape(label)}</span></button>"
    )


_EVIDENCE_FILTER_SCRIPT = """<script>
(function () {
  var table = document.getElementById("evidence-fit");
  if (!table) return;
  var inputs = table.querySelectorAll("input.col-filter");
  var boxes = document.querySelectorAll(".term-counts button[data-term]");
  var findInput = document.getElementById("replace-find");
  var columnSelect = document.getElementById("replace-column");
  var activeTerm = "";
  var termAttr = {
    make: "data-new-make",
    model: "data-new-model",
    submodel: "data-new-submodel",
    engine: "data-new-engine"
  };
  function selectedCol() {
    if (!columnSelect || columnSelect.selectedIndex < 0) return -1;
    var opt = columnSelect.options[columnSelect.selectedIndex];
    if (!opt) return -1;
    var col = parseInt(opt.getAttribute("data-col"), 10);
    return col >= 1 && col <= 5 ? col : -1;
  }
  function clearHits() {
    var hits = table.querySelectorAll("td.fit-hit");
    for (var h = 0; h < hits.length; h++) hits[h].classList.remove("fit-hit");
  }
  function apply() {
    var active = [];
    for (var i = 0; i < inputs.length; i++) {
      var q = inputs[i].value.trim().toLowerCase();
      if (!q) continue;
      var col = parseInt(inputs[i].getAttribute("data-col"), 10);
      if (col >= 0 && col <= 5) active.push({ col: col, q: q });
    }
    var find = findInput ? findInput.value : "";
    var findCol = selectedCol();
    var exact = find !== "" && findCol >= 0;
    clearHits();
    var body = table.tBodies[0];
    if (!body) return;
    var attr = activeTerm ? termAttr[activeTerm] : "";
    for (var r = 0; r < body.rows.length; r++) {
      var row = body.rows[r];
      var show = true;
      if (row.cells.length < 6) {
        show = active.length === 0 && !attr && !exact;
      } else {
        for (var a = 0; a < active.length; a++) {
          var cell = row.cells[active[a].col];
          var text = cell ? cell.textContent.toLowerCase() : "";
          if (text.indexOf(active[a].q) === -1) {
            show = false;
            break;
          }
        }
        if (show && attr && row.getAttribute(attr) !== "1") show = false;
        if (exact) {
          var target = row.cells[findCol];
          if (target && target.textContent === find) target.classList.add("fit-hit");
          else show = false;
        }
      }
      row.style.display = show ? "" : "none";
    }
  }
  function markBoxes() {
    for (var i = 0; i < boxes.length; i++) {
      var on = activeTerm !== "" && boxes[i].getAttribute("data-term") === activeTerm;
      boxes[i].classList.toggle("is-active", on);
      boxes[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
  }
  for (var i = 0; i < inputs.length; i++) {
    inputs[i].addEventListener("input", apply);
    inputs[i].addEventListener("search", apply);
  }
  if (findInput) {
    findInput.addEventListener("input", apply);
    findInput.addEventListener("search", apply);
  }
  if (columnSelect) columnSelect.addEventListener("change", apply);
  for (var b = 0; b < boxes.length; b++) {
    boxes[b].addEventListener("click", function () {
      var count = parseInt(this.getAttribute("data-count"), 10);
      if (!count) return;
      var term = this.getAttribute("data-term") || "";
      if (!termAttr[term]) return;
      activeTerm = activeTerm === term ? "" : term;
      markBoxes();
      apply();
    });
  }
})();
</script>"""


def _listing_picker(item_id: int) -> str:
    """Listing pictures waiting in the evidence card. Chosen photos stay in the left strip."""
    rows = store.listing_candidates(item_id)
    if not rows:
        return ""
    shots = []
    for row in rows:
        media_id = int(row["id"])
        shots.append(
            "<label>"
            f"<input type='checkbox' name='pick_{media_id}' value='1'>"
            f"<img src='/media/{media_id}' alt=''>"
            "</label>"
        )
    return (
        "<div class='listing-pictures'>"
        "<h2>Listing pictures</h2>"
        "<p class='muted'>From the eBay listing. They stay off this store item until you bring them across.</p>"
        f"<form method='post' action='/item/pick-photos'>"
        f"<input type='hidden' name='item_id' value='{int(item_id)}'>"
        f"<div class='candidates'>{''.join(shots)}</div>"
        "<div class='bar'><button type='submit'>Bring selected into photos</button></div>"
        "</form></div>"
    )


# Table cell index for each rename column. Year is 0 and is not a rename target.
_FITMENT_CELL_INDEX = {
    "make": 1,
    "model": 2,
    "submodel": 3,
    "variant": 4,
    "engine_code": 5,
}


def _fitment_rename(item_id: int) -> str:
    options = []
    for value, label in store.FITMENT_RENAME_COLUMNS.items():
        index = _FITMENT_CELL_INDEX.get(value)
        data_col = f" data-col='{index}'" if index is not None else ""
        options.append(f"<option value=\"{escape(value)}\"{data_col}>{escape(label)}</option>")
    return (
        f"<form method='post' action='/item/replace-fitment' class='replace-col' id='fitment-replace'>"
        f"<input type='hidden' name='item_id' value='{item_id}'>"
        f"<select name='column' id='replace-column' aria-label='Column to replace'>{''.join(options)}</select>"
        f"<input name='find' id='replace-find' placeholder='Find' aria-label='Find' autocomplete='off'>"
        f"<input name='replace' placeholder='Replace with' aria-label='Replace with' autocomplete='off'>"
        f"<button>Replace</button></form>"
    )


def _replace_summary(count: int) -> str:
    """Popup after replace. One column is one value per changed row."""
    values = "value" if count == 1 else "values"
    rows = "row" if count == 1 else "rows"
    text = escape(f"Changed {count} {values} across {count} {rows}.")
    return f"""
<dialog id="replace-summary" aria-labelledby="replace-summary-text">
<p id="replace-summary-text">{text}</p>
<div class="bar"><button type="button" id="replace-summary-close">Close</button></div>
</dialog>
<script>
(function () {{
  var dialog = document.getElementById("replace-summary");
  var closeBtn = document.getElementById("replace-summary-close");
  if (!dialog || !closeBtn) return;
  closeBtn.addEventListener("click", function () {{ dialog.close(); }});
  document.addEventListener("keydown", function (event) {{
    if (event.key !== "Escape" || !dialog.open) return;
    dialog.close();
  }});
  if (typeof dialog.showModal === "function") dialog.showModal();
}})();
</script>
"""


_OEM_LEAD = re.compile(r"^([A-Za-z0-9]{6,24})(?![A-Za-z0-9])")
_EBAY_LINK = re.compile(r"https://www\.ebay\.com\.au/(?:itm/\d+|sch/i\.html\?[^\s<]+)")
_ICON_DETAILS = (
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">'
    '<path fill="currentColor" d="M4 4h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9l-5 4v-4H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm3 4h10v1.6H7V8zm0 3.2h7v1.6H7v-1.6z"/>'
    "</svg>"
)
_ICON_EBAY = (
    '<svg viewBox="0 0 26 12" width="26" height="12" aria-hidden="true" focusable="false">'
    '<text font-family="Arial,Helvetica,sans-serif" font-size="11" font-weight="700">'
    '<tspan fill="#e53238" x="0" y="10.5">e</tspan>'
    '<tspan fill="#0064d2" x="5.2" y="10.5">b</tspan>'
    '<tspan fill="#f5af02" x="10.2" y="10.5">a</tspan>'
    '<tspan fill="#86b817" x="14.8" y="10.5">y</tspan>'
    "</text></svg>"
)
_ICON_CHECK = (
    '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" focusable="false">'
    '<path fill="currentColor" d="M6.2 10.9 3.1 7.8l1.2-1.2 1.9 1.9 5.3-5.3 1.2 1.2z"/>'
    "</svg>"
)
_ICON_TRASH = (
    '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" focusable="false">'
    '<path fill="currentColor" d="M6 1.8h4v1.1h2.8v1.3H3.2V2.9H6V1.8zM4.7 5.4h6.6l-.55 7.4a1 1 0 0 1-1 .9H6.25a1 1 0 0 1-1-.9l-.55-7.4zm1.55.15.38 6.15h1.05l-.33-6.15H6.25zm2.15 0 .33 6.15h1.05l-.38-6.15H8.4z"/>'
    "</svg>"
)
_ICON_SEND = (
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">'
    '<path fill="currentColor" d="M3.4 20.4 21 12 3.4 3.6v6.9L16.7 12 3.4 13.5v6.9z"/>'
    "</svg>"
)
_ICON_STOP = (
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">'
    '<path fill="currentColor" d="M7 7h10v10H7V7z"/>'
    "</svg>"
)
_ICON_NEW_CHAT = (
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">'
    '<path fill="currentColor" d="M4 4h11v8H8.8L6 15.2V12H4V4zm13 2h3v12h-9v-2.2L15.8 18H20V6z"/>'
    "</svg>"
)
_PART_ACTIONS = """
<script>(function(){
function field(name, value){
  var input=document.createElement('input');
  input.type='hidden';
  input.name=name;
  input.value=value;
  return input;
}
function send(action, button){
  var part=document.getElementById('part-number');
  var formRoot=document.getElementById('woo-save');
  var id=formRoot?formRoot.querySelector('input[name="item_id"]'):null;
  if(button) button.disabled=true;
  var form=document.createElement('form');
  form.method='post';
  form.action=action;
  form.appendChild(field('item_id', id?id.value:''));
  form.appendChild(field('part_number', part?part.value:''));
  document.body.appendChild(form);
  form.submit();
}
var details=document.getElementById('part-details');
var ebayBtn=document.getElementById('part-ebay');
if(details) details.addEventListener('click', function(){ send('/item/part-details', details); });
if(ebayBtn) ebayBtn.addEventListener('click', function(){ send('/item/part-ebay', ebayBtn); });
})();</script>
"""
_CHAT_SCROLL = r"""
<script>
(function () {
  var root = document.getElementById("assistant");
  var thread = document.getElementById("assistant-thread");
  if (!root || !thread) return;
  var form = root.querySelector("form");
  var box = form && form.querySelector("textarea[name=message]");
  var button = document.getElementById("assistant-send");
  var newChat = document.getElementById("assistant-new");
  var previews = form && form.querySelector(".chat-previews");
  var hintNode = thread.querySelector("p.muted");
  var hintHtml = hintNode && hintNode.parentNode === thread ? hintNode.outerHTML : "";
  var sendIcon = button ? button.innerHTML : "";
  var stopIcon = {STOP_ICON};
  var files = [];
  var busy = false;
  var controller = null;
  var kinds = {"image/png": 1, "image/jpeg": 1, "image/webp": 1, "image/gif": 1};

  function scrollThread() {
    var mode = window.getComputedStyle(thread).overflowY;
    if (mode === "auto" || mode === "scroll" || mode === "overlay") {
      thread.scrollTop = thread.scrollHeight;
      return;
    }
    var last = thread.lastElementChild;
    if (last && last.scrollIntoView) last.scrollIntoView({block: "end"});
  }

  function hideSpinner() {
    var node = thread.querySelector(".thread-wait");
    if (node) node.remove();
  }

  function showSpinner() {
    hideSpinner();
    var row = document.createElement("div");
    row.className = "thread-wait";
    row.setAttribute("role", "status");
    var spin = document.createElement("span");
    spin.className = "spin";
    spin.setAttribute("aria-hidden", "true");
    var label = document.createElement("span");
    label.textContent = "Fetching data";
    row.appendChild(spin);
    row.appendChild(label);
    thread.appendChild(row);
    scrollThread();
  }

  function showError(message) {
    hideSpinner();
    var div = document.createElement("div");
    div.className = "bubble assistant error";
    div.setAttribute("role", "alert");
    var who = document.createElement("div");
    who.className = "muted";
    who.textContent = "Assistant";
    var body = document.createElement("div");
    body.textContent = message || "The assistant could not answer.";
    div.appendChild(who);
    div.appendChild(body);
    thread.appendChild(div);
    scrollThread();
  }

  function clearHint() {
    var hint = thread.querySelector("p.muted");
    if (hint && hint.parentNode === thread) hint.remove();
  }

  function setStop() {
    busy = true;
    button.innerHTML = stopIcon;
    button.disabled = false;
    button.setAttribute("aria-label", "Stop");
    button.setAttribute("title", "Stop");
  }

  function setSend() {
    busy = false;
    controller = null;
    button.innerHTML = sendIcon;
    button.disabled = false;
    button.setAttribute("aria-label", "Send");
    button.setAttribute("title", "Send");
  }

  function resetDraft() {
    if (box && !box.disabled) box.value = "";
    files = [];
    renderPreviews();
    if (box) box.classList.remove("drop");
  }

  function showHint() {
    thread.textContent = "";
    if (hintHtml) thread.innerHTML = hintHtml;
  }

  function startNewChat() {
    if (busy && controller) controller.abort();
    hideSpinner();
    setSend();
    resetDraft();
    showHint();
    var idInput = form && form.querySelector("input[name=item_id]");
    var body = new FormData();
    body.append("item_id", idInput ? idInput.value : "");
    fetch("/item/chat-clear", {method: "POST", body: body}).catch(function () {});
  }

  function isImage(file) {
    var type = String(file.type || "").toLowerCase();
    if (type === "image/jpg") type = "image/jpeg";
    if (kinds[type]) return true;
    if (type && type !== "application/octet-stream") return false;
    return /\.(png|jpe?g|webp|gif)$/i.test(String(file.name || ""));
  }

  function renderPreviews() {
    if (!previews) return;
    Array.prototype.forEach.call(previews.querySelectorAll("img"), function (img) {
      if (String(img.src).indexOf("blob:") === 0) URL.revokeObjectURL(img.src);
    });
    previews.textContent = "";
    files.forEach(function (file) {
      var img = document.createElement("img");
      img.alt = "";
      img.width = 72;
      img.height = 54;
      img.src = URL.createObjectURL(file);
      previews.appendChild(img);
    });
  }

  function addFiles(list) {
    var before = files.length;
    Array.prototype.forEach.call(list, function (file) {
      if (files.length >= 4) return;
      if (!isImage(file)) return;
      files.push(file);
    });
    if (files.length !== before) renderPreviews();
  }

  if (box) {
    box.addEventListener("dragover", function (event) {
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
      if (!busy && !box.disabled) box.classList.add("drop");
    });
    box.addEventListener("dragleave", function () { box.classList.remove("drop"); });
    box.addEventListener("drop", function (event) {
      event.preventDefault();
      box.classList.remove("drop");
      if (busy || box.disabled) return;
      var dropped = event.dataTransfer && event.dataTransfer.files;
      if (!dropped || !dropped.length) return;
      addFiles(dropped);
    });
  }

  if (button) {
    button.addEventListener("click", function (event) {
      if (!busy) return;
      event.preventDefault();
      if (controller) controller.abort();
    });
  }

  if (newChat) {
    newChat.addEventListener("click", function () {
      if (newChat.disabled) return;
      startNewChat();
    });
  }

  if (form && box && button && previews) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (busy) return;
      var text = String(box.value || "").trim();
      if (!text && !files.length) return;
      var pending = files.slice();
      var thumbs = pending.map(function (file) { return URL.createObjectURL(file); });
      box.value = "";
      files = [];
      renderPreviews();
      clearHint();
      var user = document.createElement("div");
      user.className = "bubble user";
      var who = document.createElement("div");
      who.className = "muted";
      who.textContent = "You";
      user.appendChild(who);
      if (text) {
        var said = document.createElement("div");
        said.textContent = text;
        user.appendChild(said);
      }
      thumbs.forEach(function (url) {
        var img = document.createElement("img");
        img.className = "chat-shot";
        img.alt = "";
        img.width = 140;
        img.height = 96;
        img.src = url;
        user.appendChild(img);
      });
      thread.appendChild(user);
      scrollThread();
      showSpinner();
      setStop();
      controller = new AbortController();
      var body = new FormData();
      var idInput = form.querySelector("input[name=item_id]");
      body.append("item_id", idInput ? idInput.value : "");
      body.append("message", text);
      pending.forEach(function (file, index) {
        body.append("image" + index, file, file.name || ("photo-" + index + ".png"));
      });
      var hold = null;
      var got = false;
      var failed = false;
      var aborted = false;
      fetch("/item/chat", {
        method: "POST",
        body: body,
        headers: {Accept: "text/event-stream"},
        signal: controller.signal
      }).then(function (resp) {
        if (!resp.ok || !resp.body) {
          failed = true;
          showError("The assistant could not answer.");
          return;
        }
        var reader = resp.body.getReader();
        var decoder = new TextDecoder();
        var buffer = "";
        function take(line) {
          var trimmed = String(line || "").replace(/\r$/, "");
          if (trimmed.indexOf("data:") !== 0) return;
          var payload;
          try { payload = JSON.parse(trimmed.slice(5).trim()); }
          catch (err) { return; }
          if (!payload || typeof payload !== "object") return;
          if (payload.error) {
            failed = true;
            showError(String(payload.error));
            return;
          }
          if (typeof payload.token !== "string" || !payload.token) return;
          if (!got) {
            got = true;
            hideSpinner();
            var assistant = document.createElement("div");
            assistant.className = "bubble assistant";
            var name = document.createElement("div");
            name.className = "muted";
            name.textContent = "Assistant";
            hold = document.createElement("div");
            assistant.appendChild(name);
            assistant.appendChild(hold);
            thread.appendChild(assistant);
          }
          hold.textContent += payload.token;
          scrollThread();
        }
        function pump() {
          return reader.read().then(function (result) {
            if (result.done) {
              buffer += decoder.decode();
              buffer.split("\n").forEach(take);
              return;
            }
            buffer += decoder.decode(result.value, {stream: true});
            var lines = buffer.split("\n");
            buffer = lines.pop();
            lines.forEach(take);
            return pump();
          });
        }
        return pump();
      }).catch(function (err) {
        if (err && err.name === "AbortError") {
          aborted = true;
          hideSpinner();
          scrollThread();
          return;
        }
        if (!failed) showError(err && err.message ? err.message : "The assistant could not answer.");
        failed = true;
        hideSpinner();
      }).then(function () {
        hideSpinner();
        if (!got && !failed && !aborted) showError("The assistant did not reply.");
        setSend();
        scrollThread();
      });
    });
  }

  scrollThread();
  if (location.hash === "#assistant") {
    root.scrollIntoView({block: "nearest"});
    scrollThread();
  }
})();
</script>
""".replace("{STOP_ICON}", json.dumps(_ICON_STOP))


def part_number_for(item) -> str:
    """OEM number only. A stored MPN wins when it is not the SKU. Otherwise the leading name token."""
    sku = (item["canonical_sku"] or "").strip()
    mpn = (item["mpn"] or "").strip()
    if mpn and not seo.is_internal_sku(mpn, sku):
        return mpn
    match = _OEM_LEAD.match((item["name"] or "").lstrip())
    if not match:
        return ""
    token = match.group(1)
    if not any(ch.isdigit() for ch in token) or not any(ch.isalpha() for ch in token):
        return ""
    if seo.is_internal_sku(token, sku):
        return ""
    return token


def _usable_part_number(value: str, sku: str) -> str:
    text = " ".join((value or "").split())
    if not text or seo.is_internal_sku(text, sku):
        return ""
    return text


def _stored_mpn(item, form: dict) -> str:
    """Part number field wins. The SKU is never written into mpn."""
    sku = item["canonical_sku"] or ""
    if "part_number" in form:
        chosen = _usable_part_number(form.get("part_number") or "", sku)
        if chosen:
            return chosen
        chosen = _usable_part_number(form.get("mpn") or "", sku)
        if chosen:
            return chosen
        return _usable_part_number(item["mpn"] or "", sku)
    chosen = _usable_part_number(form.get("mpn") or "", sku)
    if chosen:
        return chosen
    return _usable_part_number(item["mpn"] or "", sku)


def _posted_part_number(item, form: dict) -> str:
    number = " ".join((form.get("part_number") or "").split())
    if not number:
        raise ValueError("Enter a part number first.")
    if seo.is_internal_sku(number, item["canonical_sku"] or ""):
        raise ValueError("That is the SKU. Enter the OEM part number.")
    return number


def _chat_body(content: str) -> str:
    escaped = escape(content or "")

    def link(match: re.Match) -> str:
        url = match.group(0)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'

    return _EBAY_LINK.sub(link, escaped)


def _chat_src_ok(token: str) -> bool:
    bits = token.split("/")
    if len(bits) != 4 or bits[0] != "" or bits[1] != "chat-image" or not bits[2].isdigit():
        return False
    stem, dot, ext = bits[3].partition(".")
    return (
        dot == "."
        and ext in {"png", "jpg", "webp", "gif"}
        and len(stem) == 32
        and all(ch in "0123456789abcdef" for ch in stem)
    )


def _bubble_html(role: str, content: str) -> str:
    who = "You" if role == "user" else "Assistant"
    chunks: list[str] = []
    text: list[str] = []

    def flush() -> None:
        if text:
            chunks.append(_chat_body("".join(text)))
            text.clear()

    for line in (content or "").splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[[img:") and stripped.endswith("]]"):
            flush()
            src = stripped[6:-2]
            if _chat_src_ok(src):
                chunks.append(f"<img class='chat-shot' src='{escape(src)}' alt='' width='140' height='96'>")
            continue
        text.append(line)
    flush()
    return f"<div class='bubble {role}'><div class='muted'>{who}</div>{''.join(chunks)}</div>"


def item_page(
    item_id: int,
    message: str = "",
    query: str = "",
    edit: bool = False,
    replaced: int | None = None,
) -> bytes:
    item = store.get_item(item_id)
    if not item:
        return page("Missing", "<p>That part is not in the studio.</p>")
    store.ensure_catalog_photos(item_id, item["canonical_sku"])
    aliases = store.aliases_for(item_id)
    media = store.media_for(item_id)
    fitment = store.fitment_for(item_id)
    confirmed = [a for a in aliases if a["confirmed"]]
    primary = item["mpn"] or next((a["raw"] for a in confirmed), "")
    sku = item["canonical_sku"]
    title, sentence = seo.build(
        item["name"] or primary or sku,
        primary,
        [a["raw"] for a in confirmed],
        internal_sku=sku,
    )
    if item["seo_title"]:
        title = seo.strip_internal_sku(item["seo_title"], sku)
    missing = seo.missing(
        title,
        sentence,
        ([primary] if primary else []) + [a["raw"] for a in confirmed],
        internal_sku=sku,
    )
    films = []
    for m in media:
        src = f"/media/{m['id']}"
        klass = "shot-open hero" if m["is_hero"] else "shot-open"
        hero_flag = "1" if m["is_hero"] else "0"
        note = f"PNG {m['bytes']} B" if m["png_path"] else "not png"
        caption = f"hero · {note}" if m["is_hero"] else note
        hero_form = ""
        if not m["is_hero"]:
            hero_form = (
                "<form method='post' action='/item/hero'>"
                f"<input type='hidden' name='item_id' value='{item_id}'>"
                f"<input type='hidden' name='media_id' value='{int(m['id'])}'>"
                "<button type='submit'>Set hero</button></form>"
            )
        films.append(
            "<div class='shot'>"
            f"<button type='button' class='{klass}' data-src='{src}' data-media-id='{int(m['id'])}' data-hero='{hero_flag}'>"
            f"<img src='{src}' alt=''></button>"
            f"<div class='muted'>{caption}</div>"
            f"<div class='shot-actions'>{hero_form}"
            f"<form method='post' action='/item/delete-media'><input type='hidden' name='item_id' value='{item_id}'>"
            f"<input type='hidden' name='media_id' value='{int(m['id'])}'>"
            f"<button type='submit'>Delete</button></form>"
            "</div></div>"
        )
    photo_add = (
        f"<form method='post' action='/item/add-photo' enctype='multipart/form-data' class='bar'>"
        f"<input type='hidden' name='item_id' value='{item_id}'>"
        f"<input type='file' name='photo' accept='image/*'>"
        f"<input name='photo_url' placeholder='Or paste image URL' style='flex:1'>"
        "<button type='submit' aria-label='Add photo' title='Add photo'>"
        "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16' aria-hidden='true' focusable='false'>"
        "<path fill='currentColor' d='M7 2h2v5h5v2H9v5H7V9H2V7h5z'/></svg></button></form>"
    )
    alias_rows = []
    for a in aliases:
        link = escape(a["evidence_url"] or "")
        alias_rows.append(
            "<tr>"
            f"<td>{escape(a['raw'])}</td><td>{escape(a['brand'])}</td><td>{escape(a['source'])}</td>"
            f"<td class='link' title=\"{link}\">{link}</td>"
            f"<td>{'yes' if a['confirmed'] else 'no'}</td>"
            f"<td><form method='post' action='/item/tick'><input type='hidden' name='item_id' value='{item_id}'>"
            f"<input type='hidden' name='alias_id' value='{a['id']}'>"
            f"<input type='hidden' name='confirmed' value='{0 if a['confirmed'] else 1}'>"
            f"<button>{'Untick' if a['confirmed'] else 'Tick'}</button></form></td></tr>"
        )
    fresh = store.new_term_names(item_id)
    counts = {level: len(fresh[level]) for level in fresh}
    fit_rows = []
    for f in fitment:
        klass = " class='new'" if f["match_status"] == "new" else ""
        flags = _fresh_flags(f, fresh)
        submodel = escape(f["submodel"])
        variant = escape(f["variant"])
        fit_rows.append(
            f"<tr{klass}{flags}><td>{escape(f['year'])}</td><td>{escape(f['make'])}</td><td>{escape(f['model'])}</td>"
            f"<td class='long' title=\"{submodel}\">{submodel}</td><td class='long' title=\"{variant}\">{variant}</td><td>{escape(f['engine_code'])}</td>"
            f"<td>{escape(f['match_status'])}</td><td class='act'>"
            f"<form method='post' action='/item/confirm'><input type='hidden' name='item_id' value='{item_id}'>"
            f"<input type='hidden' name='row_id' value='{f['id']}'>"
            f"<button type='submit' aria-label='Confirm' title='Confirm'>{_ICON_CHECK}</button></form>"
            f"<form method='post' action='/item/delete-fitment'><input type='hidden' name='item_id' value='{item_id}'>"
            f"<input type='hidden' name='row_id' value='{f['id']}'>"
            f"<button type='submit' aria-label='Delete' title='Delete'>{_ICON_TRASH}</button></form>"
            f"</td></tr>"
        )
    mapper = _column_mapper(item_id)
    term_summary = (
        "<div class='term-counts'>"
        + _term_count_box("make", "New makes", counts["make"])
        + _term_count_box("model", "New models", counts["model"])
        + _term_count_box("submodel", "New submodels", counts["submodel"])
        + _term_count_box("engine", "New engine codes", counts["engine_code"])
        + "</div>"
    )
    msg = f"<p class='warn'>{escape(message)}</p>" if message else ""
    summary = _replace_summary(replaced) if replaced is not None else ""
    miss = ""
    if missing:
        miss = "<p class='warn'>Not yet in the title or first sentence: " + escape(", ".join(missing)) + "</p>"
    body = f"""
    {msg}
    <form method="post" action="/item/pull" class="paste">
      <input type="hidden" name="item_id" value="{item_id}">
      <input name="url" placeholder="Paste an eBay item URL" style="flex:1">
      <button>Pull</button>
    </form>
    <div class="grid">
      <section class="card film"><h2>Photos</h2>{photo_add}{''.join(films) or '<p class="muted">No photos yet.</p>'}</section>
      <section class="card evidence"><h2>Evidence</h2>
        {_listing_picker(item_id)}
        {mapper}
        {term_summary}
        {_fitment_rename(item_id)}
        <table class="fitment" id="evidence-fit"><colgroup><col class="y"><col class="mk"><col class="md"><col class="sub"><col class="var"><col class="eng"><col class="st"><col class="act"></colgroup>
        <thead>
        <tr><th>Year</th><th>Make</th><th>Model</th><th>Submodel</th><th>Variant</th><th>Engine code</th><th>Status</th><th></th></tr>
        <tr class="filters">
          <th><input type="search" class="col-filter" data-col="0" size="1" aria-label="Filter Year" placeholder="Filter" autocomplete="off"></th>
          <th><input type="search" class="col-filter" data-col="1" size="1" aria-label="Filter Make" placeholder="Filter" autocomplete="off"></th>
          <th><input type="search" class="col-filter" data-col="2" size="1" aria-label="Filter Model" placeholder="Filter" autocomplete="off"></th>
          <th><input type="search" class="col-filter" data-col="3" size="1" aria-label="Filter Submodel" placeholder="Filter" autocomplete="off"></th>
          <th><input type="search" class="col-filter" data-col="4" size="1" aria-label="Filter Variant" placeholder="Filter" autocomplete="off"></th>
          <th><input type="search" class="col-filter" data-col="5" size="1" aria-label="Filter Engine code" placeholder="Filter" autocomplete="off"></th>
          <th></th><th></th>
        </tr>
        </thead>
        <tbody>
        {''.join(fit_rows) or '<tr><td colspan="8">No vehicles yet.</td></tr>'}
        </tbody></table>
        {_EVIDENCE_FILTER_SCRIPT}
        <h2>Numbers</h2>
        <table class="nums"><colgroup><col class="num"><col class="brand"><col class="src"><col class="link"><col class="tick"><col class="act"></colgroup><tr><th>Number</th><th>Brand</th><th>Source</th><th>Link</th><th>Ticked</th><th></th></tr>
        {''.join(alias_rows) or '<tr><td colspan="6">No numbers yet.</td></tr>'}</table>
        <form method="post" action="/item/alias" class="bar alias">
          <input type="hidden" name="item_id" value="{item_id}">
          <input name="raw" placeholder="Number you checked">
          <input name="brand" placeholder="Brand">
          <button>Add</button>
        </form>
        <form method="post" action="/item/research" class="reread"><input type="hidden" name="item_id" value="{item_id}"><button title="Reads part numbers printed on the eBay listing you already pulled, and adds each one here with that listing's link and first photo. It does not invent a number. Tick one yourself before it can publish.">Read numbers from the listing</button></form>
      </section>
      <section class="card"><h2>WordPress / WooCommerce</h2>
        <form method="post" action="/item/save" id="woo-save">
          <input type="hidden" name="item_id" value="{item_id}">
          <label>SKU</label><input value="{escape(item['canonical_sku'])}" disabled>
          <label for="part-number">Part number</label>
          <div class="part-line">
            <input id="part-number" name="part_number" value="{escape(part_number_for(item))}" autocomplete="off" spellcheck="false">
            <button type="button" class="icon" id="part-details" aria-label="Ask the assistant about this part number" title="Part details">{_ICON_DETAILS}</button>
            <button type="button" class="icon" id="part-ebay" aria-label="Search eBay for this part number" title="Search eBay">{_ICON_EBAY}</button>
          </div>
          {_PART_ACTIONS}
          <label>Name</label><input name="name" value="{escape(item['name'] or '')}">
          <label>Shelf price</label><input name="shelf_price" value="{'' if item['shelf_price'] is None else item['shelf_price']}">
          <label>Brand</label><input name="brand" value="{escape(item['brand'] or '')}">
          <label>Primary number</label><input name="mpn" value="{escape(item['mpn'] or '')}">
          <label>SEO title</label><textarea name="seo_title" rows="3">{escape(title)}</textarea>
          <p class="muted">First sentence, also sent as the description: {escape(sentence)}</p>
          {miss}
          <label class="check" title="Tick this when the part is not tied to one car, such as a tool or a fluid. Publish can then go out with no vehicle list. Leave it off when the part fits specific cars; those cars have to be confirmed first."><input type="checkbox" name="universal_part" value="1" {'checked' if item['universal_part'] else ''}> Universal part</label>
          <div class="bar"><button>Save</button></div>
        </form>
        {_woo_links(item_id, query, edit)}
        <form method="post" action="/item/publish"><input type="hidden" name="item_id" value="{item_id}">
          <div class="bar"><button>Publish to local shop</button></div>
          <p class="muted">Local WordPress only. Stock is not sent. Live Zoho is not called.</p>
        </form>
      </section>
    </div>
    {summary}
    {_photo_dialog(item_id)}
    {_chat(item_id)}
    """
    return page(item["canonical_sku"], body)


def _photo_dialog(item_id: int) -> str:
    """Large photo popup. Hover preview is separate. Set-as-hero still posts to /item/hero."""
    html = """
<dialog id="photo-view" aria-label="Photo">
<img id="photo-view-img" alt="">
<div class="bar">
<div class="pager">
<button type="button" id="photo-prev" aria-label="Previous photo">&#8592; Previous</button>
<button type="button" id="photo-next" aria-label="Next photo">Next &#8594;</button>
</div>
<form method="post" action="/item/hero" id="photo-hero-form">
<input type="hidden" name="item_id" value="__ITEM_ID__">
<input type="hidden" name="media_id" id="photo-hero-media" value="">
<button type="submit">Set as hero</button></form>
<p class="muted" id="photo-hero-state" hidden>This photo is the hero.</p>
<button type="button" id="photo-view-close">Close</button>
</div></dialog>
<div id="photo-hover" hidden aria-hidden="true"><img id="photo-hover-img" alt=""></div>
<script>(function(){
var dialog=document.getElementById('photo-view');
var img=document.getElementById('photo-view-img');
var media=document.getElementById('photo-hero-media');
var form=document.getElementById('photo-hero-form');
var state=document.getElementById('photo-hero-state');
var closeBtn=document.getElementById('photo-view-close');
var prevBtn=document.getElementById('photo-prev');
var nextBtn=document.getElementById('photo-next');
var hover=document.getElementById('photo-hover');
var hoverImg=document.getElementById('photo-hover-img');
if(!dialog||!img||!media||!form||!state||!closeBtn||!prevBtn||!nextBtn||!hover||!hoverImg)return;
document.body.appendChild(hover);
var shots=Array.prototype.slice.call(document.querySelectorAll('.film .shot-open'));
var index=0;
var hoverSrc='';
var wheelAt=0;
function show(i){
if(!shots.length)return;
index=((i%shots.length)+shots.length)%shots.length;
var btn=shots[index];
var src=btn.getAttribute('data-src')||'';
img.src=src;
media.value=btn.getAttribute('data-media-id')||'';
var isHero=btn.getAttribute('data-hero')==='1';
form.hidden=isHero;
state.hidden=!isHero;
img.alt='Photo '+(index+1)+' of '+shots.length;
dialog.setAttribute('aria-label','Photo '+(index+1)+' of '+shots.length);
}
function hideHover(){hover.hidden=true;}
function placeHover(btn){
var rect=btn.getBoundingClientRect();
var margin=8;
var gap=12;
hover.style.left='-9999px';
hover.style.top='0px';
hover.hidden=false;
var w=hover.offsetWidth;
var h=hover.offsetHeight;
var left=rect.right+gap;
var top=rect.top;
if(left+w>window.innerWidth-margin)left=rect.left-gap-w;
if(left<margin){left=margin;top=rect.top-gap-h;}
if(top+h>window.innerHeight-margin)top=window.innerHeight-margin-h;
if(top<margin)top=margin;
hover.style.left=Math.round(left)+'px';
hover.style.top=Math.round(top)+'px';
}
function showHover(btn){
if(dialog.open)return;
var src=btn.getAttribute('data-src')||'';
if(!src)return;
if(hoverSrc!==src){hoverSrc=src;hoverImg.src=src;}
placeHover(btn);
}
shots.forEach(function(btn){
btn.addEventListener('mouseenter',function(){showHover(btn);});
btn.addEventListener('mouseleave',hideHover);
btn.addEventListener('click',function(){
hideHover();
show(shots.indexOf(btn));
if(!dialog.open)dialog.showModal();
});
});
prevBtn.addEventListener('click',function(){show(index-1);});
nextBtn.addEventListener('click',function(){show(index+1);});
closeBtn.addEventListener('click',function(){dialog.close();});
dialog.addEventListener('pointerdown',function(event){
if(event.target===dialog)dialog.close();
});
dialog.addEventListener('close',function(){
var over=document.querySelector('.film .shot-open:hover');
if(over)showHover(over);else hideHover();
});
document.addEventListener('keydown',function(event){
if(!dialog.open)return;
if(event.key==='ArrowRight'){event.preventDefault();show(index+1);}
else if(event.key==='ArrowLeft'){event.preventDefault();show(index-1);}
});
dialog.addEventListener('wheel',function(event){
if(!dialog.open||shots.length<2)return;
event.preventDefault();
var line=event.deltaMode===1?40:(event.deltaMode===2?window.innerHeight:1);
var dx=event.deltaX*line;
var dy=event.deltaY*line;
var delta=Math.abs(dx)>Math.abs(dy)?dx:dy;
if(Math.abs(delta)<10)return;
var now=Date.now();
if(now-wheelAt<180)return;
wheelAt=now;
show(index+(delta>0?1:-1));
},{passive:false});
window.addEventListener('scroll',hideHover,true);
window.addEventListener('resize',hideHover);
})();</script>
"""
    return html.replace("__ITEM_ID__", str(int(item_id)))


def _chat(item_id: int) -> str:
    ready = ai.status()[0]
    bubbles = []
    for row in store.chat_for(item_id):
        role = "user" if row["role"] == "user" else "assistant"
        bubbles.append(_bubble_html(role, row["content"] or ""))
    locked = "" if ready else " disabled"
    thread = "".join(bubbles) or "<p class='muted'>Ask about this part number, the cars it fits, the title, the photos, or which catalog parts to link.</p>"
    return f"""
    <section class="card chat" id="assistant">
      <h2>Assistant</h2>
      <div class="thread" id="assistant-thread">{thread}</div>
      <form method="post" action="/item/chat" enctype="multipart/form-data">
        <input type="hidden" name="item_id" value="{item_id}">
        <div class="compose">
          <textarea name="message" rows="3" placeholder="Ask about this part, or which parts to link"{locked}></textarea>
          <button type="button" class="icon" id="assistant-new" aria-label="Start new chat" title="Start new chat"{locked}>{_ICON_NEW_CHAT}</button>
          <button type="submit" class="icon" id="assistant-send" aria-label="Send" title="Send"{locked}>{_ICON_SEND}</button>
        </div>
        <div class="chat-previews"></div>
      </form>
    </section>
    {_CHAT_SCROLL}
    """


def _part_tile(row, extra: str) -> str:
    shop_photo = store.catalog_image(row["canonical_sku"])
    if row["media_id"]:
        photo = f"<img src='/media/{int(row['media_id'])}' alt=''>"
    elif shop_photo:
        photo = f"<img src='{escape(shop_photo)}' alt=''>"
    else:
        photo = "<span class='nophoto'>No photo</span>"
    number = row["mpn"] or row["canonical_sku"]
    sku_line = ""
    if row["mpn"] and row["mpn"] != row["canonical_sku"]:
        sku_line = f"<div class='muted'>{escape(row['canonical_sku'])}</div>"
    return (
        f"<div class='linkcard'>{photo}<div><strong>{escape(number)}</strong>{sku_line}"
        f"<div class='muted'>{escape(row['name'] or '')}</div>{extra}</div></div>"
    )


def _link_form(item_id: int, other_id: int, kind: str, query: str, linked: bool) -> str:
    action = "/item/unlink" if linked else "/item/link"
    label = {
        ("upsell", True): "Unlink upsell",
        ("upsell", False): "Link upsell",
        ("crosssell", True): "Unlink cross-sell",
        ("crosssell", False): "Link cross-sell",
    }[(kind, linked)]
    return (
        f"<form method='post' action='{action}'>"
        f"<input type='hidden' name='item_id' value='{item_id}'>"
        f"<input type='hidden' name='other_id' value='{other_id}'>"
        f"<input type='hidden' name='kind' value='{kind}'>"
        f"<input type='hidden' name='q' value='{escape(query)}'>"
        f"<input type='hidden' name='edit' value='1'>"
        f"<button>{label}</button></form>"
    )


def _woo_links(item_id: int, query: str, edit: bool = False) -> str:
    upsells = list(store.links_for(item_id, "upsell"))
    crosses = list(store.links_for(item_id, "crosssell"))
    up_ids = {row["id"] for row in upsells}
    cross_ids = {row["id"] for row in crosses}
    found = store.search_parts(item_id, query)
    result_tiles = []
    for row in found:
        result_tiles.append(
            _part_tile(
                row,
                _link_form(item_id, row["id"], "upsell", query, row["id"] in up_ids)
                + _link_form(item_id, row["id"], "crosssell", query, row["id"] in cross_ids),
            )
        )
    shown = [
        "<div class='editrow'><h2>Linked products</h2>"
        "<button type='button' onclick=\"document.getElementById('link-edit').showModal()\">Edit</button></div>",
    ]
    for title, rows in (("Upsells", upsells), ("Cross-sells", crosses)):
        tiles = "".join(_part_tile(row, "") for row in rows)
        shown.append(f"<h2>{title}</h2>{tiles or '<p class=\"muted\">None yet.</p>'}")
    popup = [
        "<div class='editrow'><h2>Map linked products</h2>"
        "<div class='bar'>"
        "<button type='button' onclick=\"document.getElementById('link-edit').close()\">Save</button>"
        "<button type='button' onclick=\"document.getElementById('link-edit').close()\">Close</button>"
        "</div></div>",
        "<p class='muted'>Search for a part number. On the photo, choose Link upsell or Link cross-sell. "
        "The other part is linked back at the same time.</p>",
        f"<form method='get' action='/item' class='paste'>"
        f"<input type='hidden' name='id' value='{item_id}'>"
        f"<input type='hidden' name='edit' value='1'>"
        f"<input name='q' value='{escape(query)}' placeholder='Part number or name'>"
        f"<button>Find</button></form>",
        "".join(result_tiles) if result_tiles else ("<p class='muted'>No matching part.</p>" if query else ""),
    ]
    for title, rows, kind in (("Upsells", upsells, "upsell"), ("Cross-sells", crosses, "crosssell")):
        tiles = "".join(
            _part_tile(row, _link_form(item_id, row["id"], kind, query, True))
            for row in rows
        )
        popup.append(f"<h2>{title}</h2>{tiles or '<p class=\"muted\">None yet.</p>'}")
    suggestions = list(store.suggestions_for(item_id))
    if suggestions:
        tiles = []
        for row in suggestions:
            kind = "upsell" if row["kind"] == "upsell" else "cross-sell"
            buttons = (
                f"<form method='post' action='/item/accept-link'>"
                f"<input type='hidden' name='item_id' value='{item_id}'>"
                f"<input type='hidden' name='suggestion_id' value='{int(row['suggestion_id'])}'>"
                f"<input type='hidden' name='q' value='{escape(query)}'>"
                f"<input type='hidden' name='edit' value='1'>"
                f"<button>Link {kind}</button></form>"
                f"<form method='post' action='/item/dismiss-link'>"
                f"<input type='hidden' name='item_id' value='{item_id}'>"
                f"<input type='hidden' name='suggestion_id' value='{int(row['suggestion_id'])}'>"
                f"<input type='hidden' name='q' value='{escape(query)}'>"
                f"<input type='hidden' name='edit' value='1'>"
                f"<button>Dismiss</button></form>"
            )
            tiles.append(_part_tile(row, buttons))
        note = escape(suggestions[0]["note"] or "")
        popup.append(f"<h2>Assistant</h2><p class='muted'>{note}</p>{''.join(tiles)}")
    else:
        chats = store.chat_for(item_id)
        last = ""
        for row in reversed(chats):
            if row["role"] == "assistant":
                last = row["content"]
                break
        named = [row for row in store.parts_named_in(item_id, last) if row["id"] not in up_ids and row["id"] not in cross_ids]
        if named:
            tiles = "".join(
                _part_tile(
                    row,
                    _link_form(item_id, row["id"], "upsell", query, False)
                    + _link_form(item_id, row["id"], "crosssell", query, False),
                )
                for row in named
            )
            popup.append(f"<h2>From the assistant</h2>{tiles}")
    opener = "<script>document.getElementById('link-edit').showModal()</script>" if edit else ""
    return "".join(shown) + f"<dialog id='link-edit'>{''.join(popup)}</dialog>" + opener


def cascade_option_label(name: str) -> str:
    """Show stored terms with entities decoded once; values stay unchanged."""
    return escape(unescape(name))


def catalog_page(selected: dict[str, str] | None = None, cascade: bool = True) -> bytes:
    selected = selected or {}
    if cascade:
        options, active = store.cascade_options(selected)
    else:
        # Full lists. Picks stay checked and do not hide names in other columns.
        options, _full = store.cascade_options({})
        active = {}
        for level in store.LEVELS:
            picked = (selected.get(level) or "").strip()
            if picked in options[level]:
                active[level] = picked
    labels = {
        "year": "year",
        "make": "make",
        "model": "model",
        "submodel": "submodel",
        "variant": "variant",
        "engine_code": "engine code",
    }
    cols = []
    for level in store.LEVELS:
        radios = []
        for name in options[level]:
            checked = " checked" if active.get(level) == name else ""
            radios.append(
                f"<label><input type='radio' name='{level}' value='{escape(name)}'{checked} onchange='cascadePick(this)'> {cascade_option_label(name)}</label>"
            )
        count = len(options[level])
        cols.append(
            f"<section class='card'>"
            f"<div class='card-head'><h2>{labels[level]}</h2><span class='muted'>{count}</span></div>"
            f"<input type='search' class='cascade-search' placeholder='Filter…' autocomplete='off' aria-label='Filter {escape(labels[level])}'>"
            f"<div class='choices'>{''.join(radios) or '<p class=\"muted\">Nothing matches the columns to the left.</p>'}</div></section>"
        )
    paths = []
    for v in store.list_vehicles():
        label = " · ".join(escape(v[level] or "—") for level in store.LEVELS)
        paths.append(
            f"<tr><td>{label}</td><td><form method='post' action='/catalog/delete'>"
            f"<input type='hidden' name='id' value='{v['id']}'><button>Delete</button></form></td></tr>"
        )
    fields = "".join(
        f"<label>{labels[lvl]}<input name='{lvl}' value='{escape(active.get(lvl, ''))}'></label>"
        for lvl in store.LEVELS
    )
    cascade_checked = " checked" if cascade else ""
    clear_href = "/catalog" if cascade else "/catalog?cascade=0"
    body = f"""
    <div class="catalog-head">
      <h1>Vehicle catalog</h1>
      <div class="catalog-note">
        <label class="check catalog-cascade">
          <input type="hidden" name="cascade" value="0" form="cascade">
          <input type="checkbox" name="cascade" value="1" form="cascade"{cascade_checked} onchange="this.form.submit()">
          Cascade
        </label>
        <p class="muted">Pick a value. The columns to the right keep only names that share a product with it. Shop dropdowns are not changed here. <a href="{clear_href}">Clear</a></p>
      </div>
    </div>
    <form method="get" action="/catalog" class="cascade" id="cascade">
      {''.join(cols)}
    </form>
    <h2>Add a confirmed path</h2>
    <form method="post" action="/catalog/add" class="card addpath">
      {fields}
      <button>Add path</button>
    </form>
    <h2>Confirmed paths</h2>
    <table>{''.join(paths) or '<tr><td>No full paths yet.</td></tr>'}</table>
    <script>
    function cascadePick(input) {{
      const names = ["year","make","model","submodel","variant","engine_code"];
      const index = names.indexOf(input.name);
      for (const name of names.slice(index + 1)) {{
        for (const el of input.form.querySelectorAll("input[name='" + name + "']")) el.checked = false;
      }}
      input.form.submit();
    }}
    function cascadeFilterSearch(input) {{
      const q = input.value.trim().toLowerCase();
      const choices = input.closest(".card").querySelector(".choices");
      if (!choices) return;
      for (const label of choices.querySelectorAll("label")) {{
        const radio = label.querySelector("input[type=radio]");
        const text = label.textContent.trim().toLowerCase();
        const match = !q || text.includes(q);
        const keep = match || (radio && radio.checked);
        label.classList.toggle("cascade-hidden", !keep);
      }}
    }}
    for (const input of document.querySelectorAll("#cascade .cascade-search")) {{
      input.addEventListener("input", () => cascadeFilterSearch(input));
    }}
    </script>
    """
    return page("Vehicle catalog", body)


def flatten(prefix: str, value, out: dict) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            flatten(f"{prefix}.{key}" if prefix else str(key), child, out)
    elif isinstance(value, list):
        out[prefix] = json.dumps(value, ensure_ascii=False)
    else:
        out[prefix] = "" if value is None else str(value)


def compare_page(sku: str = "", message: str = "") -> bytes:
    woo_rows = []
    zoho = None
    note = "Zoho sandbox is not configured. No live Zoho call was made. The right column is local WordPress."
    try:
        skus = sorted(woo.list_skus())
        selected = woo.one_product(sku) if sku else None
    except Exception as exc:
        skus = []
        selected = None
        note = f"Local shop pull failed: {exc}"
    if selected:
        left: dict = {}
        right: dict = {}
        flatten("", selected, right)
        flatten("", zoho or {}, left)
        keys = sorted(set(left) | set(right))
        for key in keys:
            lv = left.get(key, "")
            rv = right.get(key, "")
            state = "aligned" if lv == rv and lv != "" else ("only one side" if lv == "" or rv == "" else "not aligned")
            woo_rows.append(
                f"<tr><td>{escape(key)}</td><td>{escape(lv)}</td><td>{escape(rv)}</td><td>{state}</td></tr>"
            )
        store.save_comparison(sku, selected, None)
    options = "".join(
        f"<option {'selected' if s == sku else ''}>{escape(s)}</option>" for s in skus
    )
    msg = f"<p class='warn'>{escape(message)}</p>" if message else ""
    body = f"""
    {msg}
    <h1>Zoho and WordPress</h1>
    <p>{escape(note)}</p>
    <form method="get" action="/compare" class="bar">
      <select name="sku"><option value="">Choose a SKU</option>{options}</select>
      <button>Compare</button>
    </form>
    <table><tr><th>Field</th><th>Zoho</th><th>WordPress</th><th></th></tr>
    {''.join(woo_rows) or '<tr><td colspan="4">Pick a SKU. The two columns are side by side.</td></tr>'}</table>
    """
    return page("Compare", body)


def _studio_return(handler) -> str:
    ref = urlparse(handler.headers.get("Referer") or "")
    host = (ref.hostname or "").lower()
    if host not in ("", "127.0.0.1", "localhost"):
        return "/"
    path = ref.path or "/"
    if not path.startswith("/") or path.startswith("//"):
        return "/"
    if ref.query:
        return path + "?" + ref.query
    return path


def redirect(handler, location: str) -> None:
    if "&m=" in location:
        base, message = location.split("&m=", 1)
        location = base + "&m=" + quote(message)
    handler.send_response(303)
    handler.send_header("Location", location)
    handler.end_headers()


def read_form(handler) -> dict:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length).decode("utf-8")
    data = parse_qs(raw, keep_blank_values=True)
    return {key: values[0] for key, values in data.items()}


def _owner_message(exc: BaseException) -> str:
    text = str(exc).strip()
    low = text.lower()
    if isinstance(exc, urllib.error.HTTPError):
        return f"eBay returned HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError) or "getaddrinfo" in low or "urlopen error" in low:
        return ebay.LOOKUP_NOTE
    return text or "Something went wrong."


def read_post(handler) -> tuple[dict, dict[str, cgi.FieldStorage]]:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length)
    content_type = handler.headers.get("Content-Type") or ""
    uploads: dict[str, cgi.FieldStorage] = {}
    if "multipart/form-data" not in content_type:
        data = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
        return {key: values[0] for key, values in data.items()}, uploads
    fs = cgi.FieldStorage(
        fp=BytesIO(raw),
        headers={"content-type": content_type},
        environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type},
    )
    form: dict = {}
    if not fs.list:
        return form, uploads
    for part in fs.list:
        if part.name and part.filename:
            uploads[part.name] = part
        elif part.name and not part.filename:
            form[part.name] = part.value
    return form, uploads


_IMAGE_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
_CHAT_NAME = re.compile(r"^[0-9a-f]{32}\.(?:png|jpg|webp|gif)$")
_KEY_LEAK = re.compile(r"sk-[A-Za-z0-9_\-]{6,}")


def _image_magic(raw: bytes, mime: str) -> bool:
    if mime == "image/png":
        return raw.startswith(b"\x89PNG\r\n\x1a\n")
    if mime == "image/jpeg":
        return raw.startswith(b"\xff\xd8\xff")
    if mime == "image/gif":
        return raw.startswith((b"GIF87a", b"GIF89a"))
    if mime == "image/webp":
        return len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
    return False


def _posted_images(uploads: dict) -> list[tuple[str, bytes]]:
    found: list[tuple[str, bytes]] = []
    for index in range(4):
        part = uploads.get(f"image{index}")
        if part is None or not getattr(part, "filename", None):
            continue
        ext = Path(str(part.filename)).suffix.lower()
        mime = _IMAGE_EXT.get(ext)
        stated = (getattr(part, "type", "") or "").split(";", 1)[0].strip().lower()
        if stated == "image/jpg":
            stated = "image/jpeg"
        if mime is None and stated in _IMAGE_EXT.values():
            mime = stated
        if mime is None or stated not in {"", "application/octet-stream", mime}:
            continue
        blob = part.file.read() if getattr(part, "file", None) is not None else b""
        if not isinstance(blob, bytes) or not blob or len(blob) > 8_000_000:
            continue
        if not _image_magic(blob, mime):
            continue
        found.append((mime, blob))
    return found


def _chat_error(exc: BaseException) -> str:
    if isinstance(exc, RuntimeError):
        text = _KEY_LEAK.sub("sk-…", str(exc)).strip()
        if text:
            return text[:300]
    return "The assistant could not answer."


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                body = home()
            elif parsed.path == "/catalog":
                selected = {level: (qs.get(level) or [""])[0] for level in store.LEVELS}
                cascade_values = qs.get("cascade") or []
                cascade = True if not cascade_values else "1" in cascade_values
                body = catalog_page(selected, cascade)
            elif parsed.path == "/compare":
                body = compare_page((qs.get("sku") or [""])[0])
            elif parsed.path == "/item":
                replaced_raw = (qs.get("replaced") or [""])[0]
                replaced = int(replaced_raw) if replaced_raw.isdigit() else None
                body = item_page(
                    int((qs.get("id") or ["0"])[0]),
                    (qs.get("m") or [""])[0],
                    (qs.get("q") or [""])[0],
                    (qs.get("edit") or [""])[0] == "1",
                    replaced,
                )
            elif parsed.path.startswith("/chat-image/"):
                self._chat_image(parsed.path)
                return
            elif parsed.path.startswith("/media/"):
                self._media(int(parsed.path.rsplit("/", 1)[-1]))
                return
            else:
                self.send_error(404)
                return
            self._html(body)
        except Exception:
            self._html(page("Error", f"<pre>{escape(traceback.format_exc())}</pre>"), 500)

    def do_POST(self):
        form, uploads = read_post(self)
        item_id = int(form.get("item_id") or 0)
        try:
            if self.path == "/assistant-prompt":
                op = (form.get("op") or "save").strip()
                key = (form.get("key") or "").strip()
                if ai.prompt_by_key(key) is None:
                    redirect(self, _studio_return(self))
                    return
                if op == "reset":
                    ai.reset_prompt(key)
                else:
                    text = form.get("prompt")
                    if not isinstance(text, str):
                        text = "" if text is None else str(text)
                    text = text.replace("\r\n", "\n").replace("\r", "\n")
                    ai.save_prompt(key, text)
                redirect(self, _studio_return(self))
                return
            if self.path == "/item/new":
                sku_typed = form.get("sku", "")
                name_typed = form.get("name", "")
                sku = sku_typed.strip()
                if not sku:
                    self._html(home("Enter a SKU.", sku_typed, name_typed))
                    return
                try:
                    new_id = store.create_item(sku, name_typed.strip())
                except store.SkuError as exc:
                    self._html(home(str(exc), sku_typed, name_typed))
                    return
                redirect(self, f"/item?id={new_id}")
                return
            if self.path == "/item/save":
                item = store.get_item(item_id)
                if not item:
                    raise RuntimeError("Missing part.")
                store.save_item(
                    item_id,
                    {
                        "name": form.get("name", ""),
                        "seo_title": form.get("seo_title", ""),
                        "shelf_price": form.get("shelf_price") or None,
                        "brand": form.get("brand", ""),
                        "mpn": _stored_mpn(item, form),
                        "universal_part": 1 if form.get("universal_part") else 0,
                    },
                )
                redirect(self, f"/item?id={item_id}&m=Saved")
                return
            if self.path == "/item/pull":
                try:
                    note = ebay.pull(item_id, form.get("url", "").strip())
                except urllib.error.HTTPError as exc:
                    note = f"eBay returned HTTP {exc.code}"
                except urllib.error.URLError:
                    note = ebay.LOOKUP_NOTE
                redirect(self, f"/item?id={item_id}&m={note}")
                return
            if self.path == "/item/template":
                columns = []
                i = 0
                allowed = set(store.MAP_FIELDS)
                while f"header_{i}" in form:
                    target = form.get(f"target_{i}", "skip")
                    if target not in allowed:
                        target = "skip"
                    extract = form.get(f"extract_{i}", "whole_cell")
                    if extract not in {"whole_cell", "one_row_per_code", "engine_codes_inside"}:
                        extract = "whole_cell"
                    columns.append(
                        {
                            "header": form[f"header_{i}"],
                            "position": i,
                            "target": target,
                            "extract": extract,
                        }
                    )
                    i += 1
                note = ebay.apply_pending(item_id, columns)
                redirect(self, f"/item?id={item_id}&m={note}")
                return
            if self.path == "/item/confirm":
                store.confirm_fitment(int(form["row_id"]))
                redirect(self, f"/item?id={item_id}&m=Vehicle added to the catalog")
                return
            if self.path == "/item/delete-fitment":
                store.delete_fitment(int(form["row_id"]))
                redirect(self, f"/item?id={item_id}&m=Vehicle removed from this part")
                return
            if self.path == "/item/replace-fitment":
                column = form.get("column") or ""
                find = form.get("find") if form.get("find") is not None else ""
                replacement = form.get("replace") if form.get("replace") is not None else ""
                if find == "":
                    redirect(self, f"/item?id={item_id}")
                    return
                count = store.replace_fitment_column(item_id, column, find, replacement)
                redirect(self, f"/item?id={item_id}&replaced={count}")
                return
            if self.path == "/item/pick-photos":
                ids = []
                for key, value in form.items():
                    if not str(key).startswith("pick_") or str(value) != "1":
                        continue
                    try:
                        ids.append(int(str(key).split("_", 1)[1]))
                    except ValueError:
                        continue
                if not ids:
                    redirect(self, f"/item?id={item_id}&m=Select a listing picture first")
                    return
                brought = store.pick_listing_photos(item_id, ids)
                word = "picture" if brought == 1 else "pictures"
                redirect(self, f"/item?id={item_id}&m=Brought {brought} {word} into photos")
                return
            if self.path == "/item/hero":
                store.set_hero(item_id, int(form["media_id"]))
                self._png(int(form["media_id"]))
                redirect(self, f"/item?id={item_id}&m=Hero set")
                return
            if self.path == "/item/delete-media":
                store.delete_media(item_id, int(form["media_id"]))
                redirect(self, f"/item?id={item_id}&m=Photo removed")
                return
            if self.path == "/item/add-photo":
                photo_url = (form.get("photo_url") or "").strip()
                upload = uploads.get("photo")
                if upload and upload.filename:
                    media_dir = store.ROOT / "data" / "studio-media" / str(item_id)
                    media_dir.mkdir(parents=True, exist_ok=True)
                    ext = Path(upload.filename).suffix.lower()
                    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}:
                        ext = ".jpg"
                    dest = media_dir / f"upload-{len(list(media_dir.glob('upload-*')))}{ext}"
                    dest.write_bytes(upload.file.read())
                    store.add_media(item_id, "", str(dest), "gallery")
                    redirect(self, f"/item?id={item_id}&m=Photo added")
                    return
                if photo_url:
                    store.add_media(item_id, photo_url, "", "gallery")
                    redirect(self, f"/item?id={item_id}&m=Photo added")
                    return
                redirect(self, f"/item?id={item_id}&m=Choose a photo file or URL")
                return
            if self.path == "/item/tick":
                store.set_alias_confirmed(int(form["alias_id"]), int(form.get("confirmed") or 0))
                redirect(self, f"/item?id={item_id}")
                return
            if self.path == "/item/alias":
                media = store.media_for(item_id)
                url = ""
                try:
                    url = _last_url(item_id)
                except RuntimeError:
                    url = ""
                store.add_alias(
                    item_id,
                    "oem",
                    form.get("brand", ""),
                    form.get("raw", ""),
                    "user",
                    url,
                    media[0]["id"] if media else None,
                )
                redirect(self, f"/item?id={item_id}&m=Number added. Tick it only after it has a link and a picture.")
                return
            if self.path == "/item/research":
                src = list((store.ROOT / "data" / "studio-media" / str(item_id)).glob("*.html"))
                if not src:
                    redirect(self, f"/item?id={item_id}&m=Pull a listing first. No number was invented.")
                    return
                note = ebay.pull(item_id, _last_url(item_id))
                redirect(self, f"/item?id={item_id}&m={note}")
                return
            if self.path == "/item/link":
                store.link_both(item_id, int(form["other_id"]), form.get("kind", ""))
                redirect(self, _item_back(item_id, form, "Linked both ways"))
                return
            if self.path == "/item/unlink":
                store.unlink_both(item_id, int(form["other_id"]), form.get("kind", ""))
                redirect(self, _item_back(item_id, form, "Link removed both ways"))
                return
            if self.path == "/item/suggest-links":
                note = ai.suggest_links(item_id)
                redirect(self, _item_back(item_id, form, note))
                return
            if self.path == "/item/accept-link":
                row = store.suggestion_row(int(form["suggestion_id"]))
                if not row or int(row["item_id"]) != item_id:
                    raise RuntimeError("That suggestion is not on this part.")
                store.link_both(item_id, int(row["other_item_id"]), row["kind"])
                redirect(self, _item_back(item_id, form, "Linked both ways"))
                return
            if self.path == "/item/dismiss-link":
                row = store.suggestion_row(int(form["suggestion_id"]))
                if row and int(row["item_id"]) == item_id:
                    store.dismiss_suggestion(int(row["id"]))
                redirect(self, _item_back(item_id, form, "Suggestion dismissed"))
                return
            if self.path == "/item/publish":
                note = publish(item_id)
                redirect(self, f"/item?id={item_id}&m={note}")
                return
            if self.path == "/item/chat":
                self._chat_stream(item_id, form, uploads)
                return
            if self.path == "/item/chat-clear":
                store.clear_chat(item_id)
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/item/part-details":
                item = store.get_item(item_id)
                if not item:
                    raise RuntimeError("Missing part.")
                ai.describe_part(item_id, _posted_part_number(item, form))
                redirect(self, f"/item?id={item_id}#assistant")
                return
            if self.path == "/item/part-ebay":
                item = store.get_item(item_id)
                if not item:
                    raise RuntimeError("Missing part.")
                number = _posted_part_number(item, form)
                result = ebay.search_part(number)
                store.add_chat(item_id, "user", f"Search eBay for {number}")
                store.add_chat(item_id, "assistant", ebay.search_reply(number, result)[:4000])
                redirect(self, f"/item?id={item_id}#assistant")
                return
            if self.path == "/catalog/add":
                store.add_vehicle({level: form.get(level, "") for level in store.LEVELS})
                redirect(self, "/catalog")
                return
            if self.path == "/catalog/delete":
                store.delete_vehicle(int(form["id"]))
                redirect(self, "/catalog")
                return
            self.send_error(404)
        except Exception as exc:
            message = _owner_message(exc)
            target = f"/item?id={item_id}&m={message}" if item_id else f"/?m={message}"
            redirect(self, target)

    def _chat_stream(self, item_id: int, form: dict, uploads: dict) -> None:
        self.protocol_version = "HTTP/1.1"
        self.close_connection = True
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Connection", "close")
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return
        gen = None
        try:
            images = _posted_images(uploads)
            gen = ai.stream_ask(item_id, form.get("message") or "", images)
            for token in gen:
                if token is None:
                    self._sse_raw(b": ping\n\n")
                    continue
                if token:
                    self._sse({"token": token})
            self._sse({"done": True})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as exc:
            try:
                self._sse({"error": _chat_error(exc)})
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
        finally:
            if gen is not None:
                gen.close()
            try:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except OSError:
                pass

    def _sse(self, payload: dict) -> None:
        self._sse_raw(("data: " + json.dumps(payload, ensure_ascii=False) + "\n\n").encode("utf-8"))

    def _sse_raw(self, data: bytes) -> None:
        self.wfile.write(("%X\r\n" % len(data)).encode("ascii") + data + b"\r\n")
        self.wfile.flush()

    def _chat_image(self, path: str) -> None:
        bits = [bit for bit in path.split("/") if bit]
        if len(bits) != 3 or bits[0] != "chat-image" or not bits[1].isdigit() or not _CHAT_NAME.fullmatch(bits[2]):
            self.send_error(404)
            return
        root = (store.ROOT / "data" / "studio-chat").resolve()
        file = (root / bits[1] / bits[2]).resolve()
        if root not in file.parents or not file.is_file():
            self.send_error(404)
            return
        ext = bits[2].rsplit(".", 1)[-1]
        kind = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}[ext]
        data = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "private, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def _html(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _media(self, media_id: int) -> None:
        from urllib.request import Request, urlopen

        with store.connect() as conn:
            row = conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
        if not row:
            self.send_error(404)
            return
        path = (row["png_path"] or row["original_path"] or "").strip()
        source_url = (row["source_url"] or "").strip()
        if path and Path(path).is_file():
            data = Path(path).read_bytes()
            lower = path.lower()
            if lower.endswith(".png"):
                kind = "image/png"
            elif lower.endswith(".webp"):
                kind = "image/webp"
            elif lower.endswith(".gif"):
                kind = "image/gif"
            else:
                kind = "image/jpeg"
        elif source_url:
            req = Request(source_url, headers={"User-Agent": "ydu-catalog-studio/1.0"})
            with urlopen(req, timeout=30) as resp:
                data = resp.read()
                kind = resp.headers.get("Content-Type") or "image/jpeg"
                if ";" in kind:
                    kind = kind.split(";", 1)[0].strip()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _png(self, media_id: int) -> None:
        with store.connect() as conn:
            row = conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
        if not row or not row["original_path"]:
            return
        from pathlib import Path

        dest, nbytes = woo.to_png(Path(row["original_path"]))
        store.set_png(media_id, str(dest), nbytes)

    def log_message(self, fmt, *args):
        return


def _item_back(item_id: int, form: dict, message: str) -> str:
    query = quote(form.get("q") or "", safe="")
    edit = "&edit=1" if form.get("edit") else ""
    return f"/item?id={item_id}&q={query}{edit}&m={message}"


def _last_url(item_id: int) -> str:
    with store.connect() as conn:
        row = conn.execute(
            "SELECT url FROM sources WHERE item_id = ? ORDER BY id DESC LIMIT 1",
            (item_id,),
        ).fetchone()
    if not row:
        raise RuntimeError("No listing has been pulled for this part.")
    return row["url"]


def _vehicle_note(result: dict) -> str:
    vehicles = result.get("vehicles")
    if not isinstance(vehicles, dict):
        return "Vehicle tags were included on the local product."
    added_raw = vehicles.get("added")
    added = [str(name) for name in added_raw if str(name).strip()] if isinstance(added_raw, list) else []
    try:
        kept = int(vehicles.get("kept_count") or 0)
    except (TypeError, ValueError):
        kept = 0
    listed = ""
    if added:
        shown = added[:8]
        listed = ", ".join(shown)
        if len(added) > len(shown):
            listed += f", and {len(added) - len(shown)} more"
    if added and kept:
        return f"Vehicle tags already on the local product were kept ({kept}). Added {listed}."
    if added:
        return f"Vehicle tags written on the local product: {listed}."
    if kept:
        return f"Vehicle tags already on the local product were kept ({kept})."
    return "No vehicle tags were written on the local product."


def publish(item_id: int) -> str:
    item = store.get_item(item_id)
    if not item:
        return "Missing part."
    aliases = [a for a in store.aliases_for(item_id) if a["confirmed"]]
    primary = item["mpn"] or next((a["raw"] for a in aliases), "")
    sku = item["canonical_sku"]
    built_title, sentence = seo.build(
        item["name"] or primary or sku,
        primary,
        [a["raw"] for a in aliases],
        internal_sku=sku,
    )
    title = seo.strip_internal_sku(item["seo_title"], sku) if item["seo_title"] else built_title
    missing = seo.missing(
        title,
        sentence,
        ([primary] if primary else []) + [a["raw"] for a in aliases],
        internal_sku=sku,
    )
    if missing:
        return "Publish refused. Missing from the page text: " + ", ".join(missing)
    if len(title) > 150:
        return "Publish refused. Title is over 150 characters."
    hero = next((m for m in store.media_for(item_id) if m["is_hero"]), None)
    if hero and not hero["png_path"]:
        return "Publish refused. The hero needs a PNG."
    new_rows = [r for r in store.fitment_for(item_id) if r["match_status"] == "new"]
    if new_rows and not item["universal_part"]:
        return "Publish refused. Confirm or delete the highlighted vehicles first."
    fitment = [
        {level: r[level] or "" for level in store.LEVELS}
        for r in store.fitment_for(item_id)
        if r["match_status"] == "matched"
    ]
    if not fitment and not item["universal_part"]:
        return "Publish refused. Add a vehicle or mark the part universal."
    description = sentence + "\n\n" + (item["long_description"] or "")
    result = woo.upsert(
        {
            "sku": item["canonical_sku"],
            "name": title,
            "regular_price": "" if item["shelf_price"] is None else str(item["shelf_price"]),
            "description": description,
            "short_description": item["short_description"] or "",
            "fitment": fitment,
            "hero_path": hero["png_path"] if hero else "",
            "upsell_skus": [row["canonical_sku"] for row in store.links_for(item_id, "upsell")],
            "crosssell_skus": [row["canonical_sku"] for row in store.links_for(item_id, "crosssell")],
        }
    )
    ok = bool(result.get("ok"))
    store.add_receipt(item_id, "woo-local", ok, item["canonical_sku"], json.dumps(result)[:500])
    if not ok:
        return "Local shop refused the update: " + str(result.get("error"))
    store.save_item(item_id, {"status": "published", "seo_title": title})
    missing = result.get("unresolved_links") or []
    extra = ""
    if missing:
        extra = " Not on the local shop yet: " + ", ".join(str(sku) for sku in missing) + "."
    return (
        f"Published to the local shop as product {result.get('woo_product_id')}. "
        f"{_vehicle_note(result)} Linked products were written both ways. Stock was not sent.{extra}"
    )


def main() -> None:
    store.init()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Catalog studio at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
