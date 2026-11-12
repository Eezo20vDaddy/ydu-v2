"""Read a public eBay item page and its compatibility table."""

from __future__ import annotations

import base64
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from html.parser import HTMLParser

from studio import store

UA = "YDUCatalogStudio/1.0 (local catalog tool)"
_BROWSER_LOCK = threading.Lock()
LOOKUP_NOTE = "Could not look up eBay from this computer."
_ALLOWED_HOSTS = {"www.ebay.com.au", "www.ebay.com", "ebay.com.au", "ebay.com"}
_IMAGE_HOSTS = {"i.ebayimg.com", "ebayimg.com"}
# Reduced User-Agent that desktop Chrome 156 actually sends.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/156.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://www.ebay.com.au/",
}
PART_RE = re.compile(r"\b(\d{2,3}[A-Z][0-9A-Z]{4,12})\b")
ITEM_RE = re.compile(r"/itm/(?:[^/?#]+/)?(\d{9,})")
CODE_RE = re.compile(r"\b[A-Z][A-Z0-9]{2,5}\b")
COUNT_RE = re.compile(r"compatible with\s+(\d+)\s+vehicle", re.I)
_BLOCK_TITLES = {
    "pardon our interruption",
    "security measure | ebay",
    "robot check",
}


def item_id_from_url(url: str) -> str:
    match = ITEM_RE.search(url)
    if not match:
        raise ValueError("That link does not contain an eBay item number.")
    return match.group(1)


def _host_allowed(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host in _ALLOWED_HOSTS


class _EbayRedirect(urllib.request.HTTPRedirectHandler):
    """Follow redirects only while the next host is still eBay."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _host_allowed(newurl):
            raise RuntimeError("Refused to follow a redirect off eBay.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _title_text(html: str) -> str:
    low = html.lower()
    start = low.find("<title")
    if start < 0:
        return ""
    open_end = low.find(">", start)
    close = low.find("</title>", open_end if open_end >= 0 else start)
    if open_end < 0 or close < 0:
        return ""
    return re.sub(r"\s+", " ", html[open_end + 1 : close]).strip().lower()


def _is_block_page(html: str) -> bool:
    title = _title_text(html)
    if title in _BLOCK_TITLES or "pardon our interruption" in title:
        return True
    # A full listing is large and may mention captcha in a script. A challenge
    # document is short. Do not treat a long item page as a block.
    if len(html) >= 80000:
        return False
    low = html.lower()
    return "pardon our interruption" in low or "verify you are a human" in low or "captcha" in low


def _is_error_page(html: str) -> bool:
    return _title_text(html) == "error page | ebay"


def _browser_get(url: str, timeout: int = 30) -> tuple[int, str]:
    if not _host_allowed(url):
        raise ValueError("Only ebay.com.au and ebay.com item links are fetched.")
    req = urllib.request.Request(url, headers=_BROWSER_HEADERS)
    opener = urllib.request.build_opener(_EbayRedirect)
    try:
        with opener.open(req, timeout=timeout) as resp:
            final = resp.geturl()
            if not _host_allowed(final):
                raise RuntimeError("Refused to follow a redirect off eBay.")
            status = int(resp.status or resp.getcode() or 0)
            return status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        return int(exc.code), raw.decode("utf-8", "replace")


def fetch(url: str) -> str:
    if not _host_allowed(url):
        raise ValueError("Only ebay.com.au and ebay.com item links are fetched.")
    status, body = _browser_get(url)
    if status == 403:
        status, body = _browser_get(url)
    if status != 200:
        if _is_block_page(body):
            raise RuntimeError(
                f"eBay returned HTTP {status}. The response is a block page. The listing was not read."
            )
        if _is_error_page(body):
            raise RuntimeError(
                f"eBay returned HTTP {status}. The response is an error page, not the listing."
            )
        raise RuntimeError(f"eBay returned HTTP {status}")
    return body


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self.images: list[str] = []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
        elif tag == "img":
            src = attr.get("src") or attr.get("data-src") or ""
            if "ebayimg.com" in src:
                self.images.append(src.split("?")[0])

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def _compatibility_tables(html: str) -> tuple[list[str], list[dict], int | None]:
    parser = TableParser()
    parser.feed(html)
    count_match = COUNT_RE.search(html)
    count = int(count_match.group(1)) if count_match else None
    best: tuple[list[str], list[dict]] = ([], [])
    for table in parser.tables:
        headers = table[0]
        if len(headers) < 3:
            continue
        rows = []
        for raw in table[1:]:
            if len(raw) < len(headers):
                raw = raw + [""] * (len(headers) - len(raw))
            rows.append(dict(zip(headers, raw[: len(headers)])))
        if len(rows) > len(best[1]):
            best = (headers, rows)
    return best[0], best[1], count


_CODE_TOKEN = r"[A-Z][A-Z0-9]{2,5}"
_TRAILING_CODES = re.compile(
    rf"^(?P<text>.*?)\s*(?P<codes>{_CODE_TOKEN}(?:\s*,\s*{_CODE_TOKEN})+)\s*$"
)
_TRAILING_CODE = re.compile(rf"^(?P<text>.*?)\s+(?P<code>{_CODE_TOKEN})\s*$")
_NOT_ENGINE = {
    "AWD", "FWD", "RWD", "4WD", "2WD",
    "TDI", "TSI", "TFSI", "FSI", "MPI", "GTI", "SDI", "CDI", "HDI",
    "MPV", "SUV", "DSG", "ABS",
}
_SPLIT_EXTRACTS = {"engine_codes_inside", "one_row_per_code"}
_SKIP_TARGETS = {"ignore", "raw_only", "skip"}
_HEADER_FIELDS = {
    "year": "year",
    "make": "make",
    "model": "model",
    "submodel": "submodel",
    "sub model": "submodel",
    "variant": "variant",
    "engine code": "engine_code",
    "engine_code": "engine_code",
    "engine codes": "engine_code",
    "engine": "skip",
    "notes": "skip",
    "note": "skip",
}


def peel_engine_codes(value: str) -> tuple[str, list[str], bool]:
    """Split a cell into descriptive text and engine codes.

    Returns (text, codes, separated_cleanly). A clean split peels a trailing
    code or comma-separated code list off the words in front of it. When the
    codes cannot be separated safely, text is the whole cell and separated_cleanly
    is false. Codes are still returned so they are not dropped.
    """
    raw = (value or "").strip()
    if not raw:
        return "", [], True
    match = _TRAILING_CODES.match(raw)
    if match:
        codes = [c.strip() for c in match.group("codes").split(",") if c.strip()]
        codes = [c for c in dict.fromkeys(codes) if c not in _NOT_ENGINE]
        text = match.group("text").strip(" ,")
        if len(codes) >= 2:
            return text, codes, True
    match = _TRAILING_CODE.match(raw)
    if match:
        code = match.group("code")
        text = match.group("text").strip(" ,")
        if code not in _NOT_ENGINE and text:
            return text, [code], True
    if re.fullmatch(_CODE_TOKEN, raw) and raw not in _NOT_ENGINE:
        return "", [raw], True
    embedded = re.search(
        rf"(?<![A-Z0-9])({_CODE_TOKEN}(?:\s*,\s*{_CODE_TOKEN})+)(?![A-Z0-9])",
        raw,
    )
    if embedded:
        codes = [c.strip() for c in embedded.group(1).split(",") if c.strip()]
        codes = [c for c in dict.fromkeys(codes) if c not in _NOT_ENGINE]
        if len(codes) >= 2:
            return raw, codes, False
    return raw, [], True


def _column_dict(col) -> dict:
    if isinstance(col, dict):
        return col
    return {key: col[key] for key in col.keys()}


def map_rows(headers: list[str], raw: dict, columns) -> list[dict]:
    """Map one listing row onto one or more internal vehicle rows."""
    base = {key: "" for key in ("year", "make", "model", "submodel", "variant", "engine_display", "engine_code", "notes")}
    by_header = {}
    for col in columns:
        item = _column_dict(col)
        name = (item.get("source_header") or item.get("header") or "").strip().lower()
        if name:
            by_header[name] = item
    split_value = None
    split_target = None
    for header in headers:
        col = by_header.get(header.strip().lower())
        if not col:
            continue
        value = raw.get(header, "")
        value = "" if value is None else str(value)
        target = col.get("target") or "skip"
        extract = col.get("extract") or "whole_cell"
        if target in _SKIP_TARGETS:
            continue
        if extract in _SPLIT_EXTRACTS:
            split_value = value
            split_target = target
            continue
        if target in base:
            base[target] = value
    if split_value is None:
        return [base]
    text, codes, clean = peel_engine_codes(split_value)
    if not codes:
        if split_target in base:
            base[split_target] = split_value
        return [base]
    rows = []
    for code in codes:
        row = dict(base)
        if split_target == "engine_code":
            row["engine_code"] = code
            if not row["variant"]:
                row["variant"] = text if clean else split_value
        else:
            if clean and split_target == "variant":
                row["variant"] = text
            elif clean and split_target in row:
                row[split_target] = text
            elif split_target == "variant" or split_target not in row:
                row["variant"] = split_value
            elif split_target in row:
                row[split_target] = split_value
            row["engine_code"] = code
        rows.append(row)
    return rows


def _samples_for(rows: list[dict], header: str, limit: int = 8) -> list[str]:
    found = []
    for row in rows:
        if len(found) >= limit:
            break
        value = row.get(header, "")
        value = "" if value is None else str(value).strip()
        if value:
            found.append(value)
    return found


def _looks_like_engine_display(value: str) -> bool:
    low = value.lower()
    return any(token in low for token in ("cc", "kw", "petrol", "diesel", "hybrid"))


def enforce_mapping_rules(columns: list[dict], headers: list[str], rows: list[dict]) -> list[dict]:
    """Keep the mapping on the existing vehicle fields. Skip display and notes."""
    by_header = {str(col.get("header") or "").strip().lower(): col for col in columns}
    kept: list[dict] = []
    used: set[str] = set()
    for header in headers:
        col = by_header.get(header.strip().lower(), {})
        target = str(col.get("target") or "skip").strip()
        extract = str(col.get("extract") or "whole_cell").strip()
        if target not in store.MAP_FIELDS:
            target = "skip"
        if extract == "engine_codes_inside":
            extract = "one_row_per_code"
        if extract not in {"whole_cell", "one_row_per_code"}:
            extract = "whole_cell"
        key = header.strip().lower()
        samples = _samples_for(rows, header)
        multi = any(len(peel_engine_codes(sample)[1]) >= 2 for sample in samples)
        descriptive = any(peel_engine_codes(sample)[0].strip() for sample in samples)
        if key in {"notes", "note"}:
            target, extract = "skip", "whole_cell"
        elif key == "engine" and any(_looks_like_engine_display(sample) for sample in samples):
            target, extract = "skip", "whole_cell"
        elif key in {"engine code", "engine_code", "engine codes"} and target == "skip":
            target = "engine_code"
        if multi and target == "engine_code" and descriptive:
            target = "variant"
        if multi and target == "skip" and key == "variant":
            target = "variant"
        if multi and target in {"variant", "engine_code"}:
            extract = "one_row_per_code"
        if target != "skip":
            if target in used and extract != "one_row_per_code":
                target, extract = "skip", "whole_cell"
            else:
                used.add(target)
        kept.append({"header": header, "target": target, "extract": extract})
    return kept


def heuristic_mapping(headers: list[str], rows: list[dict]) -> list[dict]:
    """Header-name mapping used when the assistant does not return one."""
    columns = []
    for header in headers:
        target = _HEADER_FIELDS.get(header.strip().lower(), "skip")
        columns.append({"header": header, "target": target, "extract": "whole_cell"})
    return enforce_mapping_rules(columns, headers, rows)


def _saved_image_url(src: str) -> str | None:
    parsed = urllib.parse.urlparse(src.strip())
    if parsed.scheme not in {"http", "https"}:
        return None
    host = (parsed.hostname or "").lower()
    if host not in _IMAGE_HOSTS:
        return None
    return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))


def _image_suffix(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return ".png"
    if data.startswith(b"GIF8"):
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ".jpg"


def _store_images(item_id: int, media_dir, sources: list[str], *, reader=None) -> tuple[int | None, int, int]:
    chosen: list[str] = []
    for src in dict.fromkeys(sources):
        if reader is not None:
            raw = src.strip()
            if raw.startswith("//"):
                raw = "https:" + raw
            cleaned = _saved_image_url(raw)
            if not cleaned:
                continue
            chosen.append(cleaned)
        elif "ebayimg.com" in src:
            chosen.append(src.split("?")[0])
        if len(chosen) >= 8:
            break
    first_media = None
    stored = 0
    failed = 0
    for index, src in enumerate(chosen):
        existing = store.media_id_for_source(item_id, src)
        data = b""
        try:
            if reader is not None:
                data = reader(src)
            else:
                data = urllib.request.urlopen(
                    urllib.request.Request(src, headers={"User-Agent": UA}), timeout=30
                ).read()
        except Exception:
            data = b""
        if not data:
            if existing is not None:
                stored += 1
                if first_media is None:
                    first_media = existing
            else:
                failed += 1
            continue
        if existing is not None:
            stored += 1
            if first_media is None:
                first_media = existing
            continue
        dest = media_dir / f"ebay-{index}{_image_suffix(data)}"
        dest.write_bytes(data)
        mid = store.add_media(
            item_id,
            src,
            str(dest),
            "gallery" if index else "evidence",
            1,
        )
        stored += 1
        if first_media is None:
            first_media = mid
    return first_media, stored, failed


def _apply_listing(item_id: int, html: str, url: str, ebay_id: str, *, image_reader=None) -> str:
    media_dir = store.ROOT / "data" / "studio-media" / str(item_id)
    media_dir.mkdir(parents=True, exist_ok=True)
    raw_path = media_dir / f"{ebay_id}.html"
    raw_path.write_text(html, encoding="utf-8")
    blocked = _is_block_page(html)
    if blocked or _is_error_page(html):
        if blocked:
            note = "eBay returned a block page. The listing was not read."
        else:
            note = "eBay returned an error page. The listing was not read."
        store.record_source(item_id, url, ebay_id, str(raw_path), note)
        return note
    parser = TableParser()
    parser.feed(html)
    first_media, _, _ = _store_images(
        item_id, media_dir, parser.images, reader=image_reader
    )
    headers, rows, count = _compatibility_tables(html)
    note = "Listing fetched."
    if not headers:
        note = "No compatibility table was in the listing HTML."
    else:
        template = store.find_template(headers)
        if template is None:
            note = "New table header. Map the columns before these rows can fill the catalog."
            pending = media_dir / "pending-table.json"
            import json
            pending.write_text(
                json.dumps({"headers": headers, "rows": rows, "count": count, "url": url, "ebay_id": ebay_id}),
                encoding="utf-8",
            )
        else:
            cols = [dict(c) for c in store.template_columns(template["id"])]
            stored = _store_fitment(item_id, template["id"], headers, rows, cols, url, ebay_id)
            got = len(rows)
            note = f"Header matched. Stored {stored} vehicle rows from {got} listing rows."
            if count and got < count:
                note += " Further pages were not in this response."
    for token in dict.fromkeys(PART_RE.findall(html)):
        store.add_alias(item_id, "oem", "", token, "ebay", url, first_media)
    store.record_source(item_id, url, ebay_id, str(raw_path), note)
    return note


def _installed_chrome() -> str:
    candidates = [
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return ""


def _chrome_major(binary: str) -> int:
    if not binary:
        return 0
    majors: list[int] = []
    root = os.path.dirname(binary)
    try:
        names = os.listdir(root)
    except OSError:
        return 0
    for name in names:
        if not name[:1].isdigit() or not os.path.isdir(os.path.join(root, name)):
            continue
        major = name.split(".", 1)[0]
        if major.isdigit():
            majors.append(int(major))
    return max(majors) if majors else 0


def _prefer_win64_driver() -> None:
    """Chrome for Testing publishes win64 only. The driver package still asks for win32."""
    import undetected_chromedriver.patcher as patcher

    current = patcher.Patcher._set_platform_name
    if getattr(current, "_ydu_win64", False):
        return

    def _set_platform_name(self) -> None:
        current(self)
        if getattr(self, "platform_name", "") == "win32" and not getattr(self, "is_old_chromedriver", False):
            self.platform_name = "win64"

    _set_platform_name._ydu_win64 = True
    patcher.Patcher._set_platform_name = _set_platform_name


def _hide_automation(driver) -> None:
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"},
        )
    except Exception:
        pass
    try:
        ua = driver.execute_script("return navigator.userAgent") or ""
    except Exception:
        ua = ""
    if "Headless" in ua:
        try:
            driver.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {"userAgent": ua.replace("Headless", "")},
            )
        except Exception:
            pass


def _chrome_sentence(exc: BaseException) -> str:
    line = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    line = re.sub(r"\s+", " ", line)
    if len(line) > 160:
        line = line[:160].rstrip()
    return f"Chrome could not open the listing. {line}"


def _quit_browser(driver) -> None:
    if driver is None:
        return
    try:
        driver.quit()
    except Exception:
        pass


def _start_chrome():
    import undetected_chromedriver as uc

    _prefer_win64_driver()
    uc.Chrome.__del__ = lambda self: None
    options = uc.ChromeOptions()
    options.page_load_strategy = "eager"
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--lang=en-AU")
    binary = _installed_chrome()
    kwargs = {
        "options": options,
        "headless": True,
        "use_subprocess": True,
        "no_sandbox": False,
    }
    major = _chrome_major(binary)
    if major:
        kwargs["version_main"] = major
    if binary:
        kwargs["browser_executable_path"] = binary
    # Temporary profile only. No proxy and no copy of the user's Chrome profile.
    driver = uc.Chrome(**kwargs)
    driver.set_page_load_timeout(45)
    driver.set_script_timeout(30)
    return driver


def _page_source(driver) -> str:
    try:
        return driver.page_source or ""
    except Exception:
        return ""


def _product_title(html: str) -> bool:
    title = _title_text(html)
    if not title or title in _BLOCK_TITLES or title == "error page | ebay":
        return False
    return title.endswith("| ebay") and len(title) > len("error page | ebay")


def _challenge_page(html: str) -> bool:
    if not html or _is_error_page(html):
        return False
    title = _title_text(html)
    if title in _BLOCK_TITLES or "pardon our interruption" in title:
        return True
    if len(html) >= 80000:
        return False
    low = html.lower()
    return (
        "checking your browser" in low
        or "pardon our interruption" in low
        or "verify you are a human" in low
    )


def _listing_ready(html: str, ebay_id: str) -> bool:
    if not html or _challenge_page(html) or _is_error_page(html) or _is_block_page(html):
        return False
    if ebay_id and ebay_id in html and ("ebayimg.com" in html.lower() or "<table" in html.lower()):
        return True
    return _product_title(html)


def _load_listing(driver, url: str, ebay_id: str) -> str:
    _hide_automation(driver)
    deadline = time.monotonic() + 40
    try:
        driver.get(url)
    except Exception:
        pass
    html = _page_source(driver)
    saw_error = False
    while time.monotonic() < deadline:
        if _challenge_page(html):
            saw_error = False
            time.sleep(1.0)
            html = _page_source(driver)
            continue
        if _is_error_page(html):
            if not saw_error:
                saw_error = True
                time.sleep(1.5)
                html = _page_source(driver)
                continue
            return html
        if _listing_ready(html, ebay_id):
            time.sleep(0.8)
            return _page_source(driver) or html
        time.sleep(0.6)
        html = _page_source(driver)
    return html


def _image_bytes(driver, src: str) -> bytes:
    from selenium.webdriver.support.ui import WebDriverWait

    cleaned = _saved_image_url(src)
    if not cleaned:
        raise ValueError("That image is not on an eBay image host.")
    try:
        driver.get(cleaned)
    except Exception:
        pass
    try:
        current = driver.current_url
    except Exception as exc:
        raise RuntimeError("The image page did not stay open.") from exc
    if (urllib.parse.urlparse(current).hostname or "").lower() not in _IMAGE_HOSTS:
        raise RuntimeError("Refused to read an image that left eBay.")
    html = _page_source(driver)
    if _is_error_page(html) or _is_block_page(html):
        raise RuntimeError("eBay did not return the image.")
    WebDriverWait(driver, 15).until(
        lambda d: d.execute_script(
            "const i=document.querySelector('img'); return !!(i && i.complete && i.naturalWidth>0);"
        )
    )
    encoded = driver.execute_async_script(
        """
        const done = arguments[0];
        const img = document.querySelector('img');
        const src = (img && (img.currentSrc || img.src)) || '';
        fetch(src).then(function (response) {
          if (!response.ok) throw new Error('status');
          return response.arrayBuffer();
        }).then(function (buf) {
          const bytes = new Uint8Array(buf);
          let binary = '';
          const chunk = 8192;
          for (let i = 0; i < bytes.length; i += chunk) {
            binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
          }
          done(btoa(binary));
        }).catch(function () { done(''); });
        """
    )
    if not encoded:
        raise RuntimeError("The image bytes were not in the browser.")
    data = base64.b64decode(encoded)
    if len(data) < 32:
        raise RuntimeError("The image bytes were not in the browser.")
    return data


def _pull_in_chrome(item_id: int, url: str, ebay_id: str) -> str:
    driver = None
    try:
        try:
            driver = _start_chrome()
        except Exception as exc:
            return _chrome_sentence(exc)
        html = _load_listing(driver, url, ebay_id)
        try:
            current = driver.current_url
        except Exception as exc:
            return _chrome_sentence(exc)
        if not _host_allowed(current):
            return "Refused to read a page that left eBay."
        if _is_block_page(html) or _is_error_page(html):
            return _apply_listing(item_id, html, url, ebay_id)
        if not ((ebay_id and ebay_id in html) or _product_title(html)):
            media_dir = store.ROOT / "data" / "studio-media" / str(item_id)
            media_dir.mkdir(parents=True, exist_ok=True)
            raw_path = media_dir / f"{ebay_id}.html"
            raw_path.write_text(html, encoding="utf-8")
            note = "The listing did not appear in Chrome."
            store.record_source(item_id, url, ebay_id, str(raw_path), note)
            return note

        def reader(src: str) -> bytes:
            return _image_bytes(driver, src)

        return _apply_listing(item_id, html, url, ebay_id, image_reader=reader)
    finally:
        _quit_browser(driver)


def pull(item_id: int, url: str) -> str:
    ebay_id = item_id_from_url(url)
    if not _host_allowed(url):
        raise ValueError("Only ebay.com.au and ebay.com item links are fetched.")
    with _BROWSER_LOCK:
        return _pull_in_chrome(item_id, url, ebay_id)


def _store_fitment(item_id: int, template_id: int, headers: list[str], raw_rows: list[dict], cols, url: str, ebay_id: str) -> int:
    stored = 0
    for raw in raw_rows:
        for mapped in map_rows(headers, raw, cols):
            store.add_fitment(item_id, template_id, 1, raw, mapped, url, ebay_id)
            stored += 1
    return stored


def apply_pending(item_id: int, columns: list[dict]) -> str:
    import json

    pending = store.ROOT / "data" / "studio-media" / str(item_id) / "pending-table.json"
    if not pending.exists():
        return "There is no unsaved table on this part."
    payload = json.loads(pending.read_text(encoding="utf-8"))
    headers = payload["headers"]
    sample = list(payload["rows"][0].values()) if payload["rows"] else []
    tid = store.save_template(headers, sample, columns)
    cols = [dict(c) for c in store.template_columns(tid)]
    stored = _store_fitment(item_id, tid, headers, payload["rows"], cols, payload["url"], payload["ebay_id"])
    pending.unlink()
    return f"Template saved. Stored {stored} vehicle rows from {len(payload['rows'])} listing rows."


def search_page_url(part: str) -> str:
    """Public ebay.com.au search for one part number. No login and no other site."""
    return "https://www.ebay.com.au/sch/i.html?_nkw=" + urllib.parse.quote(part, safe="")


_SEARCH_MARKERS = (
    "s-item__link",
    "s-item__title",
    "srp-results",
    "srp-river-results",
    "srp-river",
    "s-card__link",
    "su-card-container",
    "srp-main-content",
    "brwrvr__item-card",
)
_SKIP_TITLES = {
    "shop on ebay",
    "new listing",
    "results matching fewer words",
    "click to see more",
}


def _search_page_blocked(html: str) -> bool:
    if not html:
        return False
    if _is_error_page(html) or _is_block_page(html):
        return True
    title = _title_text(html)
    return any(
        phrase in title
        for phrase in ("pardon our interruption", "robot check", "security measure", "access denied")
    )


def _is_search_results(html: str) -> bool:
    """A real search-results document, not an item page and not a block page."""
    if not html or _search_page_blocked(html):
        return False
    title = _title_text(html)
    if "ebay" not in title:
        return False
    low = html.lower()
    return any(marker in low for marker in _SEARCH_MARKERS)


def _plain_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment or "")
    text = unescape(text).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(?:new listing\s+)+", "", text, flags=re.I)
    text = re.sub(r"\s+opens in a new window(?: or tab)?\.?$", "", text, flags=re.I)
    return text.strip(" -|")


def _good_title(text: str) -> bool:
    if not text or len(text) < 4:
        return False
    low = text.lower()
    if low in _SKIP_TITLES or low.startswith("shop on ebay"):
        return False
    return True


def _item_id_from_href(href: str) -> str:
    cleaned = unescape(href or "").replace("&amp;", "&").strip()
    if cleaned.startswith("//"):
        cleaned = "https:" + cleaned
    elif cleaned.startswith("/"):
        cleaned = "https://www.ebay.com.au" + cleaned
    host = (urllib.parse.urlparse(cleaned).hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        return ""
    match = ITEM_RE.search(cleaned)
    return match.group(1) if match else ""


def _anchor_title(attrs: str, inner: str) -> str:
    text = _plain_text(inner)
    if _good_title(text):
        return text[:180]
    for pattern in (
        r"""aria-label\s*=\s*(['"])(.*?)\1""",
        r"""\balt\s*=\s*(['"])(.*?)\1""",
        r"""\btitle\s*=\s*(['"])(.*?)\1""",
    ):
        found = re.search(pattern, attrs, flags=re.I | re.S) or re.search(pattern, inner, flags=re.I | re.S)
        if not found:
            continue
        text = _plain_text(found.group(2))
        if _good_title(text):
            return text[:180]
    return ""


def _extract_listings(html: str, limit: int = 8) -> list[dict]:
    """Item title and ebay.com.au link. Only call this on a real results page."""
    found: list[dict] = []
    seen: set[str] = set()
    for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, flags=re.I | re.S):
        href_match = re.search(r"""href\s*=\s*(['"])(.*?)\1""", match.group(1), flags=re.I | re.S)
        if not href_match:
            continue
        item_id = _item_id_from_href(href_match.group(2))
        if not item_id or item_id in seen:
            continue
        title = _anchor_title(match.group(1), match.group(2))
        if not title:
            continue
        seen.add(item_id)
        found.append({"title": title, "url": f"https://www.ebay.com.au/itm/{item_id}"})
        if len(found) >= limit:
            break
    return found


def classify_search_page(html: str, url: str) -> dict:
    """Decide whether HTML is a results page, a block/error page, or neither.

    Listings are returned only for a results page. A block or error page never
    counts as found listings.
    """
    if _search_page_blocked(html or ""):
        return {"url": url, "blocked": True, "listings": [], "kind": "blocked"}
    if _is_search_results(html or ""):
        return {
            "url": url,
            "blocked": False,
            "listings": _extract_listings(html or ""),
            "kind": "results",
        }
    return {"url": url, "blocked": False, "listings": [], "kind": "unknown"}


def search_reply(part: str, result: dict) -> str:
    """Assistant-thread text. Does not claim listings when the page was blocked."""
    url = str(result.get("url") or search_page_url(part))
    note = str(result.get("note") or "").strip()
    if note:
        return (
            f"The eBay search for {part} could not be read. {note} "
            "No listings were read.\n"
            f"Open the search: {url}"
        )
    if result.get("blocked") or result.get("kind") == "blocked":
        return (
            f"eBay blocked the search for {part}. No listings were read.\n"
            f"Open the search: {url}"
        )
    listings = result.get("listings") or []
    if result.get("kind") == "results" and listings:
        lines = [f"eBay listings for {part}:"]
        for row in listings:
            lines.append(f"{row['title']}\n{row['url']}")
        return "\n".join(lines)
    if result.get("kind") == "results":
        return (
            f"The eBay search page for {part} did not include any listing links.\n"
            f"Open the search: {url}"
        )
    return (
        f"eBay did not return a search results page for {part}, so no listings were read. "
        "The search may have been blocked.\n"
        f"Open the search: {url}"
    )


def _search_in_chrome(url: str) -> tuple[str, str]:
    """Open a search URL in the existing headless Chrome. No proxy, cookies, or login."""
    if not _host_allowed(url):
        return "", "Refused to open a page that is not eBay."
    driver = None
    try:
        try:
            driver = _start_chrome()
        except Exception as exc:
            return "", _chrome_sentence(exc)
        _hide_automation(driver)
        try:
            driver.get(url)
        except Exception:
            pass
        try:
            current = driver.current_url or ""
        except Exception:
            current = ""
        if current and not _host_allowed(current):
            return "", "Refused to read a page that left eBay."
        html = _page_source(driver)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if _search_page_blocked(html):
                return html, ""
            if _is_search_results(html) and _extract_listings(html):
                return html, ""
            time.sleep(0.6)
            html = _page_source(driver)
        return html, ""
    finally:
        _quit_browser(driver)


def search_part(part_number: str) -> dict:
    """Search ebay.com.au for one part number. Does not pull a listing into the catalog.

    A plain fetch is used first. Headless Chrome runs only when that fetch is not a
    real results page. Captchas are not solved.
    """
    part = " ".join((part_number or "").split())
    if not part:
        raise ValueError("Enter a part number first.")
    if len(part) > 60:
        raise ValueError("That part number is too long to search.")
    url = search_page_url(part)
    status = 0
    html = ""
    try:
        status, html = _browser_get(url, timeout=20)
    except Exception:
        status, html = 0, ""
    parsed = classify_search_page(html, url)
    if status == 200 and parsed["kind"] == "results":
        return parsed
    with _BROWSER_LOCK:
        chrome_html, problem = _search_in_chrome(url)
    if problem:
        return {"url": url, "blocked": True, "listings": [], "kind": "blocked", "note": problem}
    return classify_search_page(chrome_html, url)
