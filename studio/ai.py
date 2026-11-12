"""Chat with the owner's OpenAI account. The key stays in .env."""

from __future__ import annotations

import base64
import json
import os
import queue
import threading
import urllib.error
import urllib.request
import uuid

from studio import store

ROOT = store.ROOT
ENV_PATH = ROOT / ".env"
API_URL = "https://api.openai.com/v1/chat/completions"


def load_env() -> None:
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def status() -> tuple[bool, str]:
    load_env()
    if os.environ.get("OPENAI_API_KEY", "").strip():
        model = os.environ.get("OPENAI_MODEL", "").strip() or "gpt-4.1-mini"
        return True, f"OpenAI ({model}). The key stays in .env on this computer."
    return False, "Put OPENAI_API_KEY in .env in the project folder. Copy .env.example if you need the line. Sending a message reads that file."


DEFAULT_ASSISTANT_PROMPT = (
    "You are the car-parts specialist for the owner of YDU PARTS. Do what the owner asks. "
    "Your job is to answer whatever they ask—not only the part open in the catalog studio. "
    "Go deep on automotive parts: OEM and aftermarket identification, what a part does, fitment, "
    "supersession and revision chains, and cross-referencing (especially VAG Group: VW, Audi, Porsche, Skoda, Seat, Cupra often use different numbers for the same item). "
    "Bring full parts-counter and cataloging expertise; explain trade-offs and common mistakes plainly. "
    "Part numbers are exact strings: 03L198119B and 03L198119F are different numbers. "
    "Use your parts knowledge freely for research, explanation, and cross-reference suggestions. "
    "When the owner needs numbers treated as confirmed for this studio (ticks, aliases, or copy presented as stocked fact), "
    "only assert numbers backed by open_part evidence or what they pasted in the message; otherwise label them unverified "
    "and say what would confirm them (listing, supplier sheet, photo). "
    "When both numbers are evidenced for the open line, both belong in the title or first description sentence. "
    "When they want form copy, answer in plain sentences they can paste. "
    "Fitment order: year, make, model, submodel, variant, engine code. Engine codes (e.g. CNEA) come from variant, not displacement alone. "
    "For studio linked products only: upsells and cross-sells are WooCommerce links stored both ways. "
    "Name SKUs only from catalog_parts_you_may_name; do not invent SKUs; say when nothing in that list fits. "
    "The owner confirms links on screen with part number and photo. "
    "Do not tell the owner to edit ydu.com.au, the clone, or live Zoho. Stock quantity is outside this chat. "
    "\n\nopen_part (JSON for the line open in studio—use only when their question is about that line or studio workflow):\n"
    "{{open_part}}"
)
DEFAULT_CHAT_PROMPT = (
    "You are the VAG parts engineer for the owner of YDU PARTS. This chat is deep research on the open catalog line. "
    "Think, then make an engineering call. Do not answer with a list of links or unread search results. "
    "There is no live web tool on this call. Work only from the open part below, the owner's message, "
    "listing text already in this conversation, and any photo dropped on this turn. "
    "Decipher those sources the way a parts counter would: read the exact characters, the suffix, the brand mark, "
    "and any second number printed beside an OEM-looking number. "
    "If an OEM number, a fitment, or a supersession is not in that material, call it unverified. Do not invent one.\n\n"
    "Part numbers are exact strings. 03L198119F is not 03L198119B. "
    "A different character is a different part until the material in front of you shows they are the same item. Do not collapse them.\n\n"
    "When the owner names a vehicle, check fit before you describe the part. "
    "Compare that vehicle with the open part and with any application written in the listing text or on the photo. "
    "If the number does not fit that vehicle, say the mismatch first: the number, the vehicle, and why "
    "(year, chassis, engine code, or the number belonging to a different application). "
    "If the material does not show that vehicle either way, say the fit is unverified. Do not guess a fit. "
    "When you do state fitment, use this order: year, make, model, submodel, variant, engine code. "
    "An engine code comes from a printed code or the variant, not from displacement alone.\n\n"
    "Pull Chinese and aftermarket cross-reference numbers out separately from the OEM number. "
    "Listings and packaging often print a factory or supplier code beside an OEM-looking number. "
    "Label that second number as a Chinese or aftermarket cross-reference, and name the brand or supplier when the source shows it. "
    "A cross-reference is not proof the OEM fits a car, and it is not itself the OEM.\n\n"
    "Keep three layers apart in the answer. "
    "What the open part shows. "
    "What a pasted source shows (listing text or a photo) — quote the string you are reading. "
    "What you are inferring — say that it is inference, and use it only to interpret the material in front of you.\n\n"
    "End with a short engineering call: what you would record on this part, what you would not record, and what is still unproven.\n\n"
    "Do not tell the owner to edit ydu.com.au, the clone, or live Zoho. "
    "Do not publish, tick a number, or change the catalog from this chat. Stock quantity is outside this chat.\n\n"
    "open_part (JSON for the line open in studio):\n"
    "{{open_part}}"
)
_OPEN_PART = "{{open_part}}"
_PART_NUMBER = "{{part_number}}"
_CATALOG = "{{catalog}}"
_TABLE = "{{table}}"
DEFAULT_PART_PROMPT = (
    "Give details on part number {{part_number}}. "
    "This is the OEM part number, not the catalog SKU. "
    "Say what the part is and which vehicles it is associated with. "
    "Details about this exact number are welcome. "
    "Do not state any other OEM, superseded, or cross-brand number as a confirmed fact. "
    "If you mention another number, call it unverified."
)
DEFAULT_PHOTO_PROMPT = (
    "The owner attached a photo on this turn. "
    "Suggest likely VAG part numbers that are visible or identifiable from the photo, plus details and links. "
    "Label them as candidates from the photo, not as confirmed catalog facts. "
    "Do not write them onto the part, do not tick them, and do not invent a number that is presented as already stocked. "
    "If you name a number, say it came from the photo."
)
DEFAULT_PHOTO_CAPTION = "Look at the attached photo and suggest likely part numbers."
DEFAULT_LINK_SYSTEM = "Return JSON only. Never invent a SKU. Use the catalog list and nothing else."
DEFAULT_LINK_REQUEST = (
    "Choose WooCommerce linked products for this part. "
    "Upsells are alternatives shown on the product page. Cross-sells are parts bought with it. "
    "Use only SKUs from the catalog list. Do not invent a part number. "
    'Reply with JSON only: {"upsells":["SKU"],"crosssells":["SKU"],"why":"one sentence"}. '
    "Leave a list empty when nothing in the catalog fits.\n\n"
    "{{catalog}}"
)
DEFAULT_EBAY_SYSTEM = (
    "Return JSON only. Map each eBay compatibility column onto an existing vehicle field. "
    "Allowed fields are year, make, model, submodel, variant, engine_code, and skip. "
    "Never invent a field."
)
DEFAULT_EBAY_REQUEST = (
    "Map these eBay columns.\n"
    'The Engine column is a display string such as "2995cc 245kW (Petrol)". That is not an engine code. Map it to skip.\n'
    "Notes has no internal field. Map it to skip.\n"
    "Engine codes look like CAKA or CDLC. They often sit at the end of the Variant cell, separated by commas.\n"
    "When words and several engine codes share one cell, set that column's field to variant and its extract to one_row_per_code. "
    "The words stay the variant. Each code is stored as engine_code on its own row. Do not add a column.\n"
    "Every other mapped column uses extract whole_cell.\n"
    "If you cannot place a header, use skip.\n"
    'Reply with JSON: {"columns":[{"header":"Make","field":"make","extract":"whole_cell"}]}\n'
    "Include every header once.\n\n"
    "{{table}}"
)
PROMPTS: tuple[dict[str, str], ...] = (
    {
        "key": "assistant_prompt",
        "label": "Main",
        "note": "{{open_part}} is replaced with the open part's numbers, vehicles, and links. Nothing else is added.",
        "usage": "Sent as the system message when you click Details on the part number (POST /item/part-details); {{open_part}} is filled from the open catalog line.",
        "default": DEFAULT_ASSISTANT_PROMPT,
    },
    {
        "key": "prompt_chat",
        "label": "Chat",
        "note": "{{open_part}} is replaced with the open part's numbers, vehicles, and links. On a photo turn, the Photo prompt is appended. Nothing else is added.",
        "usage": "Sent as the system message for the part-page chat box (POST /item/chat), including when you drop a photo; {{open_part}} is filled from the open catalog line. The Photo prompt is appended to this Chat message on a photo turn.",
        "default": DEFAULT_CHAT_PROMPT,
    },
    {
        "key": "prompt_part_number",
        "label": "Part number",
        "note": "{{part_number}} is replaced with the OEM number from the Part number field. This is the user message; the Main prompt is the system message. If {{part_number}} is removed, the number is added at the start.",
        "usage": "Sent as the user message when you click Details on the part number field; the Main tab is still the system message on that same OpenAI call.",
        "default": DEFAULT_PART_PROMPT,
    },
    {
        "key": "prompt_photo",
        "label": "Photo",
        "note": "Appended to the Chat prompt when a photo is dropped on that turn.",
        "usage": "Appended to the Chat system message on chat turns where you drop a photo on the assistant message box.",
        "default": DEFAULT_PHOTO_PROMPT,
    },
    {
        "key": "prompt_photo_caption",
        "label": "Empty photo",
        "note": "User text sent with a dropped photo only when the message box is empty. A blank caption sends the built-in line.",
        "usage": "Used as the user message text on a photo-only chat turn when the message box is empty (vision request in stream_ask).",
        "default": DEFAULT_PHOTO_CAPTION,
    },
    {
        "key": "prompt_link_system",
        "label": "Links",
        "note": "System message for link suggestions. The Link request tab is sent with it as the user message.",
        "usage": "Sent as the system message when you request linked-product suggestions for the open part (POST /item/suggest-links).",
        "default": DEFAULT_LINK_SYSTEM,
    },
    {
        "key": "prompt_link_request",
        "label": "Link request",
        "note": "{{catalog}} is replaced with the open part and the catalog list as JSON. If you remove {{catalog}}, that JSON is appended.",
        "usage": "Sent as the user message on that same suggest-links call; {{catalog}} is replaced with JSON for the open part and allowed catalog SKUs.",
        "default": DEFAULT_LINK_REQUEST,
    },
    {
        "key": "prompt_ebay_system",
        "label": "eBay map",
        "note": "System message for eBay column mapping. The Map request tab is sent with it as the user message.",
        "usage": "Sent as the system message when the studio asks OpenAI to map eBay compatibility table columns (suggest_table_mapping).",
        "default": DEFAULT_EBAY_SYSTEM,
    },
    {
        "key": "prompt_ebay_request",
        "label": "Map request",
        "note": "{{table}} is replaced with the column headers and two sample rows as JSON. If you remove {{table}}, that JSON is appended.",
        "usage": "Sent as the user message on that same eBay mapping call; {{table}} is replaced with headers and two sample rows as JSON.",
        "default": DEFAULT_EBAY_REQUEST,
    },
)
_MIME_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def prompt_by_key(key: str) -> dict[str, str] | None:
    for spec in PROMPTS:
        if spec["key"] == key:
            return spec
    return None


def prompt_text(key: str = "assistant_prompt") -> str:
    spec = prompt_by_key(key)
    if spec is None:
        raise KeyError(key)
    saved = store.setting(key)
    if saved is None:
        return spec["default"]
    return saved


def save_prompt(key: str, text: str) -> None:
    if prompt_by_key(key) is None:
        raise KeyError(key)
    store.save_setting(key, text)


def reset_prompt(key: str) -> None:
    spec = prompt_by_key(key)
    if spec is None:
        raise KeyError(key)
    store.save_setting(key, spec["default"])


def ask(item_id: int, message: str, *, system_key: str = "prompt_chat") -> str:
    chunks: list[str] = []
    for token in stream_ask(item_id, message, system_key=system_key):
        if token:
            chunks.append(token)
    reply = "".join(chunks).strip()
    if not reply:
        raise RuntimeError("OpenAI replied without a message.")
    return reply


def describe_part(item_id: int, part_number: str) -> str:
    """Details for one OEM number. Main is the system message. Does not write the product."""
    number = " ".join((part_number or "").split())
    if not number:
        raise RuntimeError("Enter a part number first.")
    template = _fill(prompt_text("prompt_part_number"), item_id)
    if _PART_NUMBER in template:
        message = template.replace(_PART_NUMBER, number)
    else:
        message = f"Part number: {number}\n\n{template}".rstrip()
    return ask(item_id, message, system_key="assistant_prompt")


def stream_ask(
    item_id: int,
    message: str,
    images: list[tuple[str, bytes]] | None = None,
    *,
    system_key: str = "prompt_chat",
):
    """Yield assistant tokens as they arrive. Temperature is omitted."""
    shots = [(mime, raw) for mime, raw in (images or []) if mime in _MIME_EXT and raw][:4]
    text = (message or "").strip()
    if not text and not shots:
        raise RuntimeError("Type a message first.")
    load_env()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing from .env.")
    model = os.environ.get("OPENAI_MODEL", "").strip() or "gpt-4.1-mini"
    stored = text
    if shots:
        marks = "\n".join(f"[[img:{url}]]" for url in _save_chat_images(item_id, shots))
        stored = f"{text}\n{marks}".strip() if text else marks
    store.add_chat(item_id, "user", stored)
    prior = list(store.chat_for(item_id))
    system = _system(item_id, system_key)
    if shots and system_key == "prompt_chat":
        extra = _fill(prompt_text("prompt_photo"), item_id).strip()
        if extra:
            system += "\n\n" + extra
    messages: list[dict] = [{"role": "system", "content": system}]
    current_id = prior[-1]["id"] if prior else None
    for row in prior[-24:]:
        role = row["role"] if row["role"] in ("user", "assistant") else "user"
        if shots and current_id is not None and row["id"] == current_id:
            messages.append({"role": "user", "content": _vision_parts(text, shots)})
            continue
        messages.append({"role": role, "content": _plain_chat(row["content"])})
    parts: list[str] = []
    try:
        yield from _iter_tokens(key, model, messages, parts)
    finally:
        reply = "".join(parts).strip()
        if reply:
            store.add_chat(item_id, "assistant", reply)


def _plain_chat(content: str) -> str:
    lines = []
    saw_image = False
    for line in (content or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("[[img:/chat-image/") and stripped.endswith("]]"):
            saw_image = True
            continue
        lines.append(line)
    text = "\n".join(lines).strip()
    if saw_image and not text:
        text = "(photo attached)"
    return text[:4000]


def _save_chat_images(item_id: int, images: list[tuple[str, bytes]]) -> list[str]:
    folder = store.ROOT / "data" / "studio-chat" / str(int(item_id))
    folder.mkdir(parents=True, exist_ok=True)
    urls = []
    for mime, raw in images[:4]:
        ext = _MIME_EXT.get(mime)
        if not ext or not raw:
            continue
        name = uuid.uuid4().hex + ext
        (folder / name).write_bytes(raw)
        urls.append(f"/chat-image/{int(item_id)}/{name}")
    return urls


def _vision_parts(text: str, images: list[tuple[str, bytes]]) -> list[dict]:
    caption = text.strip()
    if not caption:
        caption = prompt_text("prompt_photo_caption").strip() or DEFAULT_PHOTO_CAPTION
    content: list[dict] = [{"type": "text", "text": caption[:4000]}]
    for mime, raw in images[:4]:
        if mime not in _MIME_EXT or not raw:
            continue
        encoded = base64.b64encode(raw).decode("ascii")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{encoded}"},
            }
        )
    return content


def _iter_tokens(key: str, model: str, messages: list[dict], parts: list[str]):
    payload = {"model": model, "messages": messages, "stream": True}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        message = _api_error(detail) or f"OpenAI returned HTTP {exc.code}."
        raise RuntimeError(message) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Could not reach OpenAI.") from exc
    lines: queue.Queue = queue.Queue()

    def pump() -> None:
        try:
            while True:
                raw = resp.readline()
                lines.put(raw)
                if not raw:
                    return
        except Exception as exc:
            lines.put(exc)

    worker = threading.Thread(target=pump, daemon=True)
    worker.start()
    try:
        while True:
            try:
                item = lines.get(timeout=0.4)
            except queue.Empty:
                yield None
                continue
            if isinstance(item, Exception):
                raise item
            raw = item
            if not raw:
                break
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            if not isinstance(chunk, dict):
                continue
            err = chunk.get("error")
            if isinstance(err, dict) and err.get("message"):
                raise RuntimeError(str(err.get("message"))[:300])
            choices = chunk.get("choices")
            if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                continue
            delta = choices[0].get("delta")
            if not isinstance(delta, dict):
                continue
            token = delta.get("content")
            if not token:
                continue
            token = str(token)
            parts.append(token)
            yield token
    finally:
        resp.close()
        worker.join(timeout=1)


def _part_json(item_id: int) -> str:
    item = store.get_item(item_id)
    aliases = [
        {
            "number": row["raw"],
            "brand": row["brand"],
            "source": row["source"],
            "link": row["evidence_url"],
            "ticked": bool(row["confirmed"]),
        }
        for row in store.aliases_for(item_id)
    ]
    cars = [
        {
            "year": row["year"],
            "make": row["make"],
            "model": row["model"],
            "submodel": row["submodel"],
            "variant": row["variant"],
            "engine_code": row["engine_code"],
            "status": row["match_status"],
        }
        for row in store.fitment_for(item_id)[:40]
    ]
    links = {
        "upsells": [row["canonical_sku"] for row in store.links_for(item_id, "upsell")],
        "crosssells": [row["canonical_sku"] for row in store.links_for(item_id, "crosssell")],
    }
    catalog = [
        {"sku": row["canonical_sku"], "name": row["name"], "number": row["mpn"], "brand": row["brand"]}
        for row in store.link_candidates(item_id)
    ]
    payload = {
        "sku": item["canonical_sku"] if item else "",
        "name": item["name"] if item else "",
        "brand": item["brand"] if item else "",
        "primary_number": item["mpn"] if item else "",
        "shelf_price": item["shelf_price"] if item else None,
        "seo_title": item["seo_title"] if item else "",
        "numbers": aliases,
        "vehicles": cars,
        "linked_products": links,
        "catalog_parts_you_may_name": catalog,
    }
    return json.dumps(payload, ensure_ascii=False)


def _fill(text: str, item_id: int) -> str:
    if _OPEN_PART not in text:
        return text
    return text.replace(_OPEN_PART, _part_json(item_id))


def _system(item_id: int, key: str = "assistant_prompt") -> str:
    return _fill(prompt_text(key), item_id)


def _link_system(item_id: int) -> str:
    return _fill(prompt_text("prompt_link_system"), item_id)


def _put_mark(text: str, mark: str, value: str) -> str:
    if mark in text:
        return text.replace(mark, value)
    stripped = text.rstrip()
    if not stripped:
        return value
    return stripped + "\n\n" + value


def suggest_links(item_id: int) -> str:
    load_env()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing from .env.")
    model = os.environ.get("OPENAI_MODEL", "").strip() or "gpt-4.1-mini"
    item = store.get_item(item_id)
    if not item:
        raise RuntimeError("Missing part.")
    candidates = store.link_candidates(item_id)
    by_sku = {row["canonical_sku"]: row for row in candidates}
    catalog = [
        {"sku": row["canonical_sku"], "name": row["name"], "number": row["mpn"], "brand": row["brand"]}
        for row in candidates
    ]
    store.add_chat(item_id, "user", "Suggest linked products for the WordPress shop.")
    catalog_json = json.dumps(
        {
            "part": {
                "sku": item["canonical_sku"],
                "name": item["name"],
                "brand": item["brand"],
                "number": item["mpn"],
            },
            "catalog": catalog,
        },
        ensure_ascii=False,
    )
    prompt = _put_mark(_fill(prompt_text("prompt_link_request"), item_id), _CATALOG, catalog_json)
    reply = _complete(
        key,
        model,
        [
            {"role": "system", "content": _link_system(item_id)},
            {"role": "user", "content": prompt},
        ],
    )
    chosen = _parse_link_json(reply)
    rows: list[tuple[int, str, str]] = []
    kept: dict[str, list[str]] = {"upsell": [], "crosssell": []}
    note = str(chosen.get("why") or "").strip()
    for kind, source in (("upsell", "upsells"), ("crosssell", "crosssells")):
        for sku in chosen.get(source) or []:
            row = by_sku.get(str(sku))
            if not row:
                continue
            rows.append((int(row["id"]), kind, note))
            kept[kind].append(row["canonical_sku"])
    store.replace_suggestions(item_id, rows)
    summary = note or "No extra reason was given."
    if kept["upsell"] or kept["crosssell"]:
        summary += " Upsells: " + (", ".join(kept["upsell"]) or "none") + ". Cross-sells: " + (", ".join(kept["crosssell"]) or "none") + "."
        summary += " The pictures are on the WordPress / WooCommerce panel. Tick one to link it both ways."
    else:
        summary += " No catalog part was suggested."
    store.add_chat(item_id, "assistant", summary[:4000])
    return summary


def _parse_link_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _complete(
    key: str,
    model: str,
    messages: list[dict],
    timeout: int = 90,
    temperature: float | None = None,
    response_format: dict | None = None,
) -> str:
    payload: dict = {"model": model, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature
    if response_format:
        payload["response_format"] = response_format
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        message = _api_error(detail) or f"OpenAI returned HTTP {exc.code}."
        raise RuntimeError(message) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Could not reach OpenAI.") from exc
    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenAI replied without a message.") from exc


def suggest_table_mapping(headers: list[str], rows: list[dict]) -> dict:
    """Ask OpenAI to map eBay columns. Header names are used only if that call fails."""
    from studio import ebay

    samples = [row for row in rows[:2]]
    fallback_note = "The assistant did not run. Columns were filled from the header names."
    try:
        load_env()
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        model = os.environ.get("OPENAI_MODEL", "").strip() or "gpt-4.1-mini"
        if not key:
            print("table mapping assistant failed: missing key", flush=True)
            return {
                "columns": ebay.heuristic_mapping(headers, rows),
                "model_columns": [],
                "note": fallback_note,
                "openai": False,
                "model": "",
            }
        reply = _mapping_reply(key, model, headers, samples)
        parsed = _mapping_from_reply(reply, headers)
        if not parsed or not _mapping_usable(parsed):
            print("table mapping assistant failed: unusable reply", flush=True)
            return {
                "columns": ebay.heuristic_mapping(headers, rows),
                "model_columns": parsed or [],
                "note": "The assistant did not return a usable mapping. Columns were filled from the header names.",
                "openai": False,
                "model": model,
            }
        columns = ebay.enforce_mapping_rules(parsed, headers, rows)
        print(f"table mapping assistant: OpenAI {model}", flush=True)
        return {
            "columns": columns,
            "model_columns": parsed,
            "note": "",
            "openai": True,
            "model": model,
        }
    except Exception as exc:
        print(f"table mapping assistant failed: {type(exc).__name__}", flush=True)
        return {
            "columns": ebay.heuristic_mapping(headers, rows),
            "model_columns": [],
            "note": fallback_note,
            "openai": False,
            "model": "",
        }


def _mapping_reply(key: str, model: str, headers: list[str], samples: list[dict]) -> str:
    system = prompt_text("prompt_ebay_system")
    table = json.dumps({"headers": headers, "sample_rows": samples}, ensure_ascii=False)
    user = _put_mark(prompt_text("prompt_ebay_request"), _TABLE, table)
    try:
        return _complete(
            key,
            model,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            timeout=60,
            temperature=None,
            response_format={"type": "json_object"},
        )
    except RuntimeError:
        return _complete(
            key,
            model,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            timeout=60,
            temperature=None,
        )


def _mapping_from_reply(text: str, headers: list[str]) -> list[dict] | None:
    data = _parse_link_json(text)
    cols = data.get("columns")
    found: dict[str, tuple[str, str]] = {}
    if isinstance(cols, list):
        for col in cols:
            if not isinstance(col, dict):
                continue
            header = str(col.get("header") or "").strip()
            field = str(col.get("field") or col.get("target") or "").strip()
            extract = str(col.get("extract") or "whole_cell").strip()
            if header:
                found[header.lower()] = (field, extract)
    elif isinstance(cols, dict):
        for header, spec in cols.items():
            if isinstance(spec, str):
                found[str(header).strip().lower()] = (spec.strip(), "whole_cell")
            elif isinstance(spec, dict):
                field = str(spec.get("field") or spec.get("target") or "").strip()
                extract = str(spec.get("extract") or "whole_cell").strip()
                found[str(header).strip().lower()] = (field, extract)
    else:
        return None
    if not found:
        return None
    out = []
    for header in headers:
        field, extract = found.get(header.strip().lower(), ("skip", "whole_cell"))
        out.append({"header": header, "target": field, "extract": extract})
    return out


def _mapping_usable(columns: list[dict]) -> bool:
    fields = {col.get("target") for col in columns}
    return bool(fields & {"year", "make", "model", "submodel", "variant", "engine_code"})


def _api_error(raw: str) -> str:
    try:
        message = json.loads(raw)["error"]["message"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return ""
    return str(message)[:300]
