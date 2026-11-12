"""SQLite store for the local catalog studio. Not used by the shop."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "studio" / "var" / "studio.sqlite"
TEMPLATE_PATH = ROOT / "data" / "table-templates.json"
EXPORT_PATH = ROOT / "data" / "export" / "products-wc-v3.json"

LEVELS = ("year", "make", "model", "submodel", "variant", "engine_code")
MAP_FIELDS = LEVELS + ("skip",)
TARGETS = LEVELS + ("engine_display", "notes", "raw_only", "ignore", "skip")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_media_columns(conn: sqlite3.Connection) -> None:
    names = {row[1] for row in conn.execute("PRAGMA table_info(media)")}
    if "listing_candidate" not in names:
        conn.execute(
            "ALTER TABLE media ADD COLUMN listing_candidate INTEGER NOT NULL DEFAULT 0"
        )


def init() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS items (
              id INTEGER PRIMARY KEY,
              canonical_sku TEXT UNIQUE NOT NULL,
              name TEXT DEFAULT '',
              seo_title TEXT DEFAULT '',
              primary_alias_id INTEGER,
              short_description TEXT DEFAULT '',
              long_description TEXT DEFAULT '',
              shelf_price REAL,
              brand TEXT DEFAULT '',
              mpn TEXT DEFAULT '',
              gtin TEXT,
              woo_product_id INTEGER,
              zoho_item_id TEXT,
              status TEXT DEFAULT 'draft',
              universal_part INTEGER DEFAULT 0,
              updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS aliases (
              id INTEGER PRIMARY KEY,
              item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
              kind TEXT NOT NULL,
              brand TEXT DEFAULT '',
              raw TEXT NOT NULL,
              normalized TEXT NOT NULL,
              source TEXT NOT NULL,
              evidence_url TEXT DEFAULT '',
              evidence_media_id INTEGER,
              confirmed INTEGER DEFAULT 0,
              UNIQUE (item_id, kind, brand, normalized)
            );
            CREATE TABLE IF NOT EXISTS vehicles (
              id INTEGER PRIMARY KEY,
              year TEXT DEFAULT '',
              make TEXT DEFAULT '',
              model TEXT DEFAULT '',
              submodel TEXT DEFAULT '',
              variant TEXT DEFAULT '',
              engine_code TEXT DEFAULT '',
              UNIQUE (year, make, model, submodel, variant, engine_code)
            );
            CREATE TABLE IF NOT EXISTS vehicle_terms (
              id INTEGER PRIMARY KEY,
              level TEXT NOT NULL,
              name TEXT NOT NULL,
              UNIQUE (level, name)
            );
            CREATE TABLE IF NOT EXISTS table_templates (
              id INTEGER PRIMARY KEY,
              fingerprint TEXT UNIQUE NOT NULL,
              label TEXT DEFAULT '',
              created_at TEXT,
              sample_headers TEXT,
              sample_row TEXT
            );
            CREATE TABLE IF NOT EXISTS template_columns (
              id INTEGER PRIMARY KEY,
              template_id INTEGER NOT NULL REFERENCES table_templates(id) ON DELETE CASCADE,
              source_header TEXT NOT NULL,
              position INTEGER NOT NULL,
              target TEXT NOT NULL,
              extract TEXT NOT NULL DEFAULT 'whole_cell'
            );
            CREATE TABLE IF NOT EXISTS sources (
              id INTEGER PRIMARY KEY,
              item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
              url TEXT NOT NULL,
              ebay_legacy_id TEXT,
              fetched_at TEXT,
              raw_path TEXT,
              note TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS media (
              id INTEGER PRIMARY KEY,
              item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
              source_url TEXT DEFAULT '',
              original_path TEXT DEFAULT '',
              png_path TEXT DEFAULT '',
              bytes INTEGER DEFAULT 0,
              is_hero INTEGER DEFAULT 0,
              rights_confirmed INTEGER DEFAULT 0,
              role TEXT DEFAULT 'evidence',
              listing_candidate INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS fitment_rows (
              id INTEGER PRIMARY KEY,
              item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
              template_id INTEGER,
              vehicle_id INTEGER,
              match_status TEXT DEFAULT 'new',
              page_number INTEGER DEFAULT 1,
              raw_json TEXT NOT NULL,
              raw_hash TEXT NOT NULL,
              year TEXT DEFAULT '',
              make TEXT DEFAULT '',
              model TEXT DEFAULT '',
              submodel TEXT DEFAULT '',
              variant TEXT DEFAULT '',
              engine_display TEXT DEFAULT '',
              engine_code TEXT DEFAULT '',
              notes TEXT DEFAULT '',
              source TEXT DEFAULT 'ebay-table',
              evidence_url TEXT DEFAULT '',
              ebay_item_id TEXT DEFAULT '',
              confirmed INTEGER DEFAULT 0,
              UNIQUE (item_id, template_id, raw_hash)
            );
            CREATE TABLE IF NOT EXISTS comparisons (
              id INTEGER PRIMARY KEY,
              canonical_sku TEXT NOT NULL,
              pulled_at TEXT,
              zoho_item_id TEXT,
              woo_product_id INTEGER,
              zoho_json TEXT,
              woo_json TEXT,
              aligned INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS receipts (
              id INTEGER PRIMARY KEY,
              item_id INTEGER NOT NULL,
              target TEXT NOT NULL,
              ok INTEGER NOT NULL,
              request_hash TEXT,
              response_excerpt TEXT,
              created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
              id INTEGER PRIMARY KEY,
              item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS links (
              id INTEGER PRIMARY KEY,
              item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
              other_item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
              kind TEXT NOT NULL,
              UNIQUE (item_id, other_item_id, kind)
            );
            CREATE TABLE IF NOT EXISTS link_suggestions (
              id INTEGER PRIMARY KEY,
              item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
              other_item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
              kind TEXT NOT NULL,
              note TEXT DEFAULT '',
              created_at TEXT,
              UNIQUE (item_id, other_item_id, kind)
            );
            CREATE TABLE IF NOT EXISTS catalog_photo_hidden (
              item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
              url TEXT NOT NULL,
              UNIQUE (item_id, url)
            );
            CREATE TABLE IF NOT EXISTS studio_settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )
        _ensure_media_columns(conn)
        n = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
        if n == 0 and EXPORT_PATH.exists():
            _import_export(conn)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def norm_part(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def fingerprint(headers: list[str]) -> str:
    return "|".join(h.strip().lower() for h in headers)


def _import_export(conn: sqlite3.Connection) -> None:
    products = json.loads(EXPORT_PATH.read_text(encoding="utf-8"))
    slug_to_level = {
        "pa_year_alt": "year",
        "pa_make": "make",
        "pa_model": "model",
        "pa_submodel": "submodel",
        "pa_variant": "variant",
        "pa_engine_code": "engine_code",
    }
    for product in products:
        sku = (product.get("sku") or "").strip()
        if not sku:
            continue
        price = product.get("regular_price") or product.get("price") or ""
        try:
            price_n = float(price) if price != "" else None
        except ValueError:
            price_n = None
        conn.execute(
            """
            INSERT OR IGNORE INTO items
              (canonical_sku, name, shelf_price, mpn, status, updated_at)
            VALUES (?, ?, ?, ?, 'draft', ?)
            """,
            (sku, product.get("name") or sku, price_n, sku, now()),
        )
        options: dict[str, list[str]] = {level: [] for level in LEVELS}
        for attr in product.get("attributes") or []:
            level = slug_to_level.get(attr.get("slug") or "")
            if not level:
                continue
            for name in attr.get("options") or []:
                name = str(name).strip()
                if not name:
                    continue
                options[level].append(name)
                conn.execute(
                    "INSERT OR IGNORE INTO vehicle_terms (level, name) VALUES (?, ?)",
                    (level, name),
                )
        if all(len(options[level]) == 1 for level in LEVELS):
            path = tuple(options[level][0] for level in LEVELS)
            conn.execute(
                """
                INSERT OR IGNORE INTO vehicles
                  (year, make, model, submodel, variant, engine_code)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                path,
            )


def list_items() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT id, canonical_sku, name, status FROM items ORDER BY canonical_sku"
        ).fetchall()


def get_item(item_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()


def save_item(item_id: int, fields: dict) -> None:
    allowed = {
        "name",
        "seo_title",
        "short_description",
        "long_description",
        "shelf_price",
        "brand",
        "mpn",
        "universal_part",
        "status",
    }
    sets = []
    vals = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        sets.append(f"{key} = ?")
        vals.append(value)
    sets.append("updated_at = ?")
    vals.append(now())
    vals.append(item_id)
    with connect() as conn:
        conn.execute(f"UPDATE items SET {', '.join(sets)} WHERE id = ?", vals)


class SkuError(ValueError):
    """Create refused because the canonical SKU is empty or already stored."""


def create_item(sku: str, name: str = "") -> int:
    sku = sku.strip()
    if not sku:
        raise SkuError("Enter a SKU.")
    with connect() as conn:
        taken = conn.execute(
            "SELECT 1 FROM items WHERE canonical_sku = ?",
            (sku,),
        ).fetchone()
        if taken:
            raise SkuError("That SKU already exists.")
        try:
            cur = conn.execute(
                """
                INSERT INTO items (canonical_sku, name, mpn, status, updated_at)
                VALUES (?, ?, ?, 'draft', ?)
                """,
                (sku, name or sku, sku, now()),
            )
        except sqlite3.IntegrityError as exc:
            raise SkuError("That SKU already exists.") from exc
        return int(cur.lastrowid)


def add_alias(item_id: int, kind: str, brand: str, raw: str, source: str, url: str, media_id: int | None) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO aliases
              (item_id, kind, brand, raw, normalized, source, evidence_url, evidence_media_id, confirmed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (item_id, kind, brand, raw, norm_part(raw), source, url, media_id),
        )


def aliases_for(item_id: int) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM aliases WHERE item_id = ? ORDER BY id", (item_id,)
        ).fetchall()


def set_alias_confirmed(alias_id: int, confirmed: int) -> None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM aliases WHERE id = ?", (alias_id,)).fetchone()
        if not row:
            return
        if confirmed and (not row["evidence_url"] or not row["evidence_media_id"]):
            return
        conn.execute("UPDATE aliases SET confirmed = ? WHERE id = ?", (confirmed, alias_id))


def add_media(
    item_id: int,
    source_url: str,
    original_path: str,
    role: str = "evidence",
    listing_candidate: int = 0,
) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO media (item_id, source_url, original_path, role, listing_candidate)
            VALUES (?, ?, ?, ?, ?)
            """,
            (item_id, source_url, original_path, role, 1 if listing_candidate else 0),
        )
        return int(cur.lastrowid)


def set_png(media_id: int, png_path: str, nbytes: int) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE media SET png_path = ?, bytes = ? WHERE id = ?",
            (png_path, nbytes, media_id),
        )


def set_hero(item_id: int, media_id: int) -> None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id FROM media
            WHERE id = ? AND item_id = ? AND listing_candidate = 0
            """,
            (media_id, item_id),
        ).fetchone()
        if not row:
            return
        conn.execute("UPDATE media SET is_hero = 0 WHERE item_id = ?", (item_id,))
        conn.execute(
            "UPDATE media SET is_hero = 1, role = 'hero' WHERE id = ? AND item_id = ? AND listing_candidate = 0",
            (media_id, item_id),
        )


def set_rights(media_id: int, confirmed: int) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE media SET rights_confirmed = ? WHERE id = ?",
            (confirmed, media_id),
        )


def media_for(item_id: int) -> list[sqlite3.Row]:
    """Photos chosen for the store item. Listing candidates are not included."""
    with connect() as conn:
        return conn.execute(
            """
            SELECT * FROM media
            WHERE item_id = ? AND listing_candidate = 0
            ORDER BY is_hero DESC, id
            """,
            (item_id,),
        ).fetchall()


def listing_candidates(item_id: int) -> list[sqlite3.Row]:
    """Pictures downloaded from a listing and not yet brought onto the item."""
    with connect() as conn:
        return conn.execute(
            """
            SELECT * FROM media
            WHERE item_id = ? AND listing_candidate = 1
            ORDER BY id
            """,
            (item_id,),
        ).fetchall()


def media_id_for_source(item_id: int, source_url: str) -> int | None:
    source_url = source_url.strip()
    if not source_url:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id FROM media
            WHERE item_id = ? AND source_url = ?
            ORDER BY id
            LIMIT 1
            """,
            (item_id, source_url),
        ).fetchone()
    return int(row["id"]) if row else None


def pick_listing_photos(item_id: int, media_ids: list[int]) -> int:
    """Move selected listing pictures onto the item. Does not set a hero."""
    picked = 0
    with connect() as conn:
        for media_id in media_ids:
            cur = conn.execute(
                """
                UPDATE media
                SET listing_candidate = 0
                WHERE id = ? AND item_id = ? AND listing_candidate = 1
                """,
                (int(media_id), item_id),
            )
            picked += cur.rowcount
    return picked


def _media_count(item_id: int) -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM media WHERE item_id = ?",
            (item_id,),
        ).fetchone()
    return int(row["c"])


def delete_media(item_id: int, media_id: int) -> None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM media WHERE id = ? AND item_id = ?",
            (media_id, item_id),
        ).fetchone()
        if not row:
            return
        source_url = (row["source_url"] or "").strip()
        original_path = (row["original_path"] or "").strip()
        if source_url and not original_path:
            conn.execute(
                """
                INSERT OR IGNORE INTO catalog_photo_hidden (item_id, url)
                VALUES (?, ?)
                """,
                (item_id, source_url),
            )
        conn.execute(
            "UPDATE aliases SET evidence_media_id = NULL WHERE evidence_media_id = ?",
            (media_id,),
        )
        conn.execute("DELETE FROM media WHERE id = ?", (media_id,))
    for key in ("original_path", "png_path"):
        path = row[key]
        if not path:
            continue
        p = Path(path)
        if p.is_file():
            p.unlink()


def _hidden_catalog_urls(item_id: int) -> set[str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT url FROM catalog_photo_hidden WHERE item_id = ?",
            (item_id,),
        ).fetchall()
    return {str(r["url"]) for r in rows}


_EXPORT_PRODUCTS: list | None = None
_EXPORT_MTIME: float | None = None
_shop_read_blocked_until = 0.0


def _export_products() -> list:
    """June catalog export, parsed once per file change. Item pages must not re-read it per part."""
    global _EXPORT_PRODUCTS, _EXPORT_MTIME
    mtime = EXPORT_PATH.stat().st_mtime if EXPORT_PATH.exists() else 0.0
    if _EXPORT_PRODUCTS is not None and _EXPORT_MTIME == mtime:
        return _EXPORT_PRODUCTS
    products: list = []
    if EXPORT_PATH.exists():
        products = json.loads(EXPORT_PATH.read_text(encoding="utf-8"))
    _EXPORT_PRODUCTS = products
    _EXPORT_MTIME = mtime
    return products


def _export_images_for_sku(sku: str) -> list[str]:
    urls: list[str] = []
    for product in _export_products():
        if (product.get("sku") or "").strip() != sku:
            continue
        for image in product.get("images") or []:
            if not isinstance(image, dict):
                continue
            src = (image.get("src") or image.get("thumbnail") or "").strip()
            if src:
                urls.append(src)
        break
    return urls


def catalog_image_urls(sku: str) -> list[str]:
    """Product images from local WooCommerce, else the catalog export JSON.

    A dead local shop must not hold the item page. One short attempt is enough,
    then later part clicks use the export until the shop is worth trying again.
    """
    global _shop_read_blocked_until
    sku = sku.strip()
    if not sku:
        return []
    urls: list[str] = []
    if time.monotonic() >= _shop_read_blocked_until:
        try:
            from studio import woo

            product = woo.one_product(sku, timeout=2)
            if product:
                urls = [str(u).strip() for u in product.get("images") or [] if str(u).strip()]
        except RuntimeError as exc:
            urls = []
            text = str(exc).lower()
            if "timed out" in text or "not running" in text:
                _shop_read_blocked_until = time.monotonic() + 60
    if urls:
        return urls
    return _export_images_for_sku(sku)


def ensure_catalog_photos(item_id: int, sku: str) -> None:
    """When studio has no photos, mirror saved shop/export images into the media table."""
    if _media_count(item_id):
        return
    hidden = _hidden_catalog_urls(item_id)
    for url in catalog_image_urls(sku):
        if url in hidden:
            continue
        add_media(item_id, url, "", "catalog")


def find_template(headers: list[str]) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM table_templates WHERE fingerprint = ?",
            (fingerprint(headers),),
        ).fetchone()


def template_columns(template_id: int) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM template_columns WHERE template_id = ? ORDER BY position",
            (template_id,),
        ).fetchall()


def save_template(headers: list[str], sample: list[str], columns: list[dict]) -> int:
    fp = fingerprint(headers)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO table_templates (fingerprint, label, created_at, sample_headers, sample_row)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
              sample_headers = excluded.sample_headers,
              sample_row = excluded.sample_row
            """,
            (fp, " / ".join(headers), now(), json.dumps(headers), json.dumps(sample)),
        )
        row = conn.execute(
            "SELECT id FROM table_templates WHERE fingerprint = ?", (fp,)
        ).fetchone()
        tid = int(row["id"])
        conn.execute("DELETE FROM template_columns WHERE template_id = ?", (tid,))
        for col in columns:
            if col["target"] not in TARGETS:
                continue
            conn.execute(
                """
                INSERT INTO template_columns
                  (template_id, source_header, position, target, extract)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tid, col["header"], col["position"], col["target"], col.get("extract") or "whole_cell"),
            )
    _write_template_file()
    return tid


def _write_template_file() -> None:
    with connect() as conn:
        templates = []
        for tpl in conn.execute("SELECT * FROM table_templates ORDER BY id"):
            cols = [
                dict(r)
                for r in conn.execute(
                    "SELECT source_header, position, target, extract FROM template_columns WHERE template_id = ? ORDER BY position",
                    (tpl["id"],),
                )
            ]
            templates.append(
                {
                    "fingerprint": tpl["fingerprint"],
                    "label": tpl["label"],
                    "headers": json.loads(tpl["sample_headers"] or "[]"),
                    "columns": cols,
                }
            )
    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_PATH.write_text(json.dumps(templates, indent=2), encoding="utf-8")


def lookup_vehicle(path: dict) -> int | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id FROM vehicles
            WHERE year = ? AND make = ? AND model = ? AND submodel = ? AND variant = ? AND engine_code = ?
            """,
            tuple(path.get(level, "") for level in LEVELS),
        ).fetchone()
        return int(row["id"]) if row else None


def add_vehicle(path: dict) -> int:
    values = tuple((path.get(level) or "").strip() for level in LEVELS)
    with connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO vehicles
              (year, make, model, submodel, variant, engine_code)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        for level, name in zip(LEVELS, values):
            if name:
                conn.execute(
                    "INSERT OR IGNORE INTO vehicle_terms (level, name) VALUES (?, ?)",
                    (level, name),
                )
        row = conn.execute(
            """
            SELECT id FROM vehicles
            WHERE year = ? AND make = ? AND model = ? AND submodel = ? AND variant = ? AND engine_code = ?
            """,
            values,
        ).fetchone()
        return int(row["id"])


def delete_vehicle(vehicle_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
        conn.execute(
            """
            UPDATE fitment_rows
            SET vehicle_id = NULL, match_status = 'new', confirmed = 0
            WHERE vehicle_id = ?
            """,
            (vehicle_id,),
        )


def list_vehicles() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            """
            SELECT * FROM vehicles
            ORDER BY year, make, model, submodel, variant, engine_code
            """
        ).fetchall()


def list_terms() -> dict[str, list[str]]:
    out = {level: [] for level in LEVELS}
    with connect() as conn:
        for row in conn.execute(
            "SELECT level, name FROM vehicle_terms ORDER BY level, name"
        ):
            out.setdefault(row["level"], []).append(row["name"])
    return out


def new_term_names(item_id: int) -> dict[str, set[str]]:
    """Distinct evidence names on this part that are absent from the catalog term lists.

    Equality is exact and case-sensitive, the same way lookup_vehicle compares stored names.
    Blank and whitespace-only values are skipped. A row's match status does not decide membership.
    """
    levels = ("make", "model", "submodel", "engine_code")
    known = {level: set(list_terms().get(level, [])) for level in levels}
    names = {level: set() for level in levels}
    with connect() as conn:
        for level in levels:
            rows = conn.execute(
                f"""
                SELECT DISTINCT {level} AS name
                FROM fitment_rows
                WHERE item_id = ?
                  AND match_status != 'deleted'
                  AND {level} != ''
                """,
                (item_id,),
            ).fetchall()
            names[level] = {
                row["name"]
                for row in rows
                if (row["name"] or "").strip() and row["name"] not in known[level]
            }
    return names


def new_term_counts(item_id: int) -> dict[str, int]:
    """Distinct evidence names on this part that are absent from the catalog term lists.

    Equality is exact, the same way lookup_vehicle compares stored names.
    Blank values are skipped. A row's match status does not decide the count.
    """
    return {level: len(found) for level, found in new_term_names(item_id).items()}


_product_groups: list[dict[str, set[str]]] | None = None
_product_mtime: float | None = None


def _product_groups_cached() -> list[dict[str, set[str]]]:
    global _product_groups, _product_mtime
    mtime = EXPORT_PATH.stat().st_mtime if EXPORT_PATH.exists() else 0
    if _product_groups is not None and _product_mtime == mtime:
        return _product_groups
    groups: list[dict[str, set[str]]] = []
    if EXPORT_PATH.exists():
        slug_to_level = {
            "pa_year_alt": "year",
            "pa_make": "make",
            "pa_model": "model",
            "pa_submodel": "submodel",
            "pa_variant": "variant",
            "pa_engine_code": "engine_code",
        }
        products = _export_products()
        for product in products:
            group = {level: set() for level in LEVELS}
            for attr in product.get("attributes") or []:
                level = slug_to_level.get(attr.get("slug") or "")
                if not level:
                    continue
                for name in attr.get("options") or []:
                    name = str(name).strip()
                    if name:
                        group[level].add(name)
            if any(group.values()):
                groups.append(group)
    _product_groups = groups
    _product_mtime = mtime
    return groups


def cascade_options(selected: dict[str, str]) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Names at each level that share a product with the choices to the left."""
    groups = list(_product_groups_cached())
    for vehicle in list_vehicles():
        groups.append({level: {vehicle[level]} if vehicle[level] else set() for level in LEVELS})
    active: dict[str, str] = {}
    options: dict[str, list[str]] = {}
    for level in LEVELS:
        names: set[str] = set()
        for group in groups:
            if any(group[parent].isdisjoint({active[parent]}) for parent in active):
                continue
            names.update(group[level])
        options[level] = sorted(names, key=str.lower)
        picked = (selected.get(level) or "").strip()
        if picked in names:
            active[level] = picked
    return options, active


def add_fitment(item_id: int, template_id: int | None, page: int, raw: dict, mapped: dict, url: str, ebay_id: str) -> None:
    raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    # One listing row can become several fitment rows, one engine code each.
    # The unique key is the listing row plus that code, so the split rows all store.
    raw_hash = hashlib.sha256(f"{raw_json}\n{mapped.get('engine_code') or ''}".encode("utf-8")).hexdigest()
    vehicle_id = lookup_vehicle(mapped)
    status = "matched" if vehicle_id else "new"
    with connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO fitment_rows (
              item_id, template_id, vehicle_id, match_status, page_number, raw_json, raw_hash,
              year, make, model, submodel, variant, engine_display, engine_code, notes,
              source, evidence_url, ebay_item_id, confirmed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ebay-table', ?, ?, ?)
            """,
            (
                item_id,
                template_id,
                vehicle_id,
                status,
                page,
                raw_json,
                raw_hash,
                mapped.get("year", ""),
                mapped.get("make", ""),
                mapped.get("model", ""),
                mapped.get("submodel", ""),
                mapped.get("variant", ""),
                mapped.get("engine_display", ""),
                mapped.get("engine_code", ""),
                mapped.get("notes", ""),
                url,
                ebay_id,
                1 if vehicle_id else 0,
            ),
        )


def fitment_for(item_id: int) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            """
            SELECT * FROM fitment_rows
            WHERE item_id = ? AND match_status != 'deleted'
            ORDER BY match_status DESC, page_number, id
            """,
            (item_id,),
        ).fetchall()


def confirm_fitment(row_id: int) -> None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM fitment_rows WHERE id = ?", (row_id,)).fetchone()
    if not row:
        return
    path = {level: row[level] or "" for level in LEVELS}
    vid = add_vehicle(path)
    with connect() as conn:
        conn.execute(
            """
            UPDATE fitment_rows
            SET vehicle_id = ?, match_status = 'matched', confirmed = 1
            WHERE id = ?
            """,
            (vid, row_id),
        )


def delete_fitment(row_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE fitment_rows SET match_status = 'deleted', confirmed = 0 WHERE id = ?",
            (row_id,),
        )


# Year, status, and the row actions are not rename targets.
FITMENT_RENAME_COLUMNS = {
    "make": "Make",
    "model": "Model",
    "submodel": "Submodel",
    "variant": "Variant",
    "engine_code": "Engine code",
}


def replace_fitment_column(item_id: int, column: str, find: str, replacement: str) -> int:
    """Whole-cell, case-sensitive replace of one fitment column on this item.

    Returns how many visible rows matched before the write. An empty find
    writes nothing. Confirmed, status, and every other column stay as they are.
    """
    if column not in FITMENT_RENAME_COLUMNS:
        raise ValueError("That column cannot be renamed.")
    if find == "":
        return 0
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, {column} AS cell
            FROM fitment_rows
            WHERE item_id = ? AND match_status != 'deleted'
            """,
            (item_id,),
        ).fetchall()
        # Python equality is the whole cell, and it is case-sensitive.
        ids = [int(row["id"]) for row in rows if row["cell"] == find]
        if not ids:
            return 0
        conn.executemany(
            f"UPDATE fitment_rows SET {column} = ? WHERE id = ? AND item_id = ?",
            [(replacement, row_id, item_id) for row_id in ids],
        )
    return len(ids)


def record_source(item_id: int, url: str, ebay_id: str, raw_path: str, note: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO sources (item_id, url, ebay_legacy_id, fetched_at, raw_path, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item_id, url, ebay_id, now(), raw_path, note),
        )


def add_receipt(item_id: int, target: str, ok: bool, request: str, response: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO receipts (item_id, target, ok, request_hash, response_excerpt, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item_id, target, 1 if ok else 0, request[:200], response[:500], now()),
        )


def chat_for(item_id: int) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM chat_messages WHERE item_id = ? ORDER BY id",
            (item_id,),
        ).fetchall()


def add_chat(item_id: int, role: str, content: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (item_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (item_id, role, content, now()),
        )


def clear_chat(item_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM chat_messages WHERE item_id = ?", (item_id,))


def setting(key: str) -> str | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT value FROM studio_settings WHERE key = ?",
            (key,),
        ).fetchone()
    if row is None:
        return None
    return str(row["value"])


def save_setting(key: str, text: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO studio_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, text),
        )


def assistant_prompt() -> str | None:
    return setting("assistant_prompt")


def save_assistant_prompt(text: str) -> None:
    save_setting("assistant_prompt", text)


LINK_KINDS = ("upsell", "crosssell")


def catalog_image(sku: str) -> str:
    """Shop photo from the June catalog export. Studio hero photos take priority in the page."""
    sku = sku.strip()
    for product in _export_products():
        if (product.get("sku") or "").strip() != sku:
            continue
        images = product.get("images") or []
        if images and isinstance(images[0], dict):
            return images[0].get("thumbnail") or images[0].get("src") or ""
        return ""
    return ""

_PART_SQL = """
    SELECT i.id, i.canonical_sku, i.name, i.mpn, i.brand,
      (SELECT m.id FROM media m WHERE m.item_id = i.id AND m.listing_candidate = 0
       ORDER BY m.is_hero DESC, m.id LIMIT 1) AS media_id
    FROM items i
"""


def item_by_sku(sku: str) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM items WHERE canonical_sku = ?", (sku,)).fetchone()


def search_parts(item_id: int, query: str, limit: int = 24) -> list[sqlite3.Row]:
    query = query.strip()
    if not query:
        return []
    like = f"%{query}%"
    with connect() as conn:
        return conn.execute(
            _PART_SQL
            + """
            WHERE i.id != ?
              AND (i.canonical_sku LIKE ? OR i.name LIKE ? OR i.mpn LIKE ? OR i.brand LIKE ?)
            ORDER BY i.canonical_sku
            LIMIT ?
            """,
            (item_id, like, like, like, like, limit),
        ).fetchall()


def links_for(item_id: int, kind: str) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            _PART_SQL
            + """
            JOIN links l ON l.other_item_id = i.id
            WHERE l.item_id = ? AND l.kind = ?
            ORDER BY i.canonical_sku
            """,
            (item_id, kind),
        ).fetchall()


def link_both(item_id: int, other_id: int, kind: str) -> None:
    if item_id == other_id:
        raise RuntimeError("A part cannot be linked to itself.")
    if kind not in LINK_KINDS:
        raise RuntimeError("Unknown link.")
    with connect() as conn:
        other = conn.execute("SELECT id FROM items WHERE id = ?", (other_id,)).fetchone()
        if not other:
            raise RuntimeError("That part is not in the catalog.")
        for left, right in ((item_id, other_id), (other_id, item_id)):
            conn.execute(
                "INSERT OR IGNORE INTO links (item_id, other_item_id, kind) VALUES (?, ?, ?)",
                (left, right, kind),
            )
        conn.execute(
            "DELETE FROM link_suggestions WHERE (item_id = ? AND other_item_id = ? AND kind = ?) OR (item_id = ? AND other_item_id = ? AND kind = ?)",
            (item_id, other_id, kind, other_id, item_id, kind),
        )


def unlink_both(item_id: int, other_id: int, kind: str) -> None:
    if kind not in LINK_KINDS:
        raise RuntimeError("Unknown link.")
    with connect() as conn:
        conn.execute(
            "DELETE FROM links WHERE kind = ? AND ((item_id = ? AND other_item_id = ?) OR (item_id = ? AND other_item_id = ?))",
            (kind, item_id, other_id, other_id, item_id),
        )


def link_candidates(item_id: int, limit: int = 40) -> list[sqlite3.Row]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT i.id, i.canonical_sku, i.name, i.mpn, i.brand
            FROM items i
            JOIN fitment_rows f ON f.item_id = i.id
            JOIN fitment_rows mine ON mine.item_id = ?
              AND mine.make = f.make AND mine.model = f.model
              AND mine.make != '' AND mine.model != ''
            WHERE i.id != ?
            ORDER BY i.canonical_sku
            LIMIT ?
            """,
            (item_id, item_id, limit),
        ).fetchall()
        if rows:
            return rows
        brand = conn.execute("SELECT brand FROM items WHERE id = ?", (item_id,)).fetchone()
        brand_name = (brand["brand"] or "").strip() if brand else ""
        if brand_name:
            rows = conn.execute(
                "SELECT id, canonical_sku, name, mpn, brand FROM items WHERE id != ? AND brand = ? ORDER BY canonical_sku LIMIT ?",
                (item_id, brand_name, limit),
            ).fetchall()
            if rows:
                return rows
        return conn.execute(
            "SELECT id, canonical_sku, name, mpn, brand FROM items WHERE id != ? ORDER BY canonical_sku LIMIT ?",
            (item_id, limit),
        ).fetchall()


def replace_suggestions(item_id: int, rows: list[tuple[int, str, str]]) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM link_suggestions WHERE item_id = ?", (item_id,))
        for other_id, kind, note in rows:
            if kind not in LINK_KINDS or other_id == item_id:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO link_suggestions
                  (item_id, other_item_id, kind, note, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_id, other_id, kind, note[:300], now()),
            )


def suggestions_for(item_id: int) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            """
            SELECT s.id AS suggestion_id, s.kind, s.note,
              i.id, i.canonical_sku, i.name, i.mpn, i.brand,
              (SELECT m.id FROM media m WHERE m.item_id = i.id AND m.listing_candidate = 0
               ORDER BY m.is_hero DESC, m.id LIMIT 1) AS media_id
            FROM link_suggestions s
            JOIN items i ON i.id = s.other_item_id
            WHERE s.item_id = ?
            ORDER BY s.kind, i.canonical_sku
            """,
            (item_id,),
        ).fetchall()


def suggestion_row(suggestion_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM link_suggestions WHERE id = ?",
            (suggestion_id,),
        ).fetchone()


def dismiss_suggestion(suggestion_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM link_suggestions WHERE id = ?", (suggestion_id,))


def parts_named_in(item_id: int, text: str, limit: int = 8) -> list[sqlite3.Row]:
    import re

    if not text.strip():
        return []
    with connect() as conn:
        rows = conn.execute(
            _PART_SQL + " WHERE i.id != ? ORDER BY length(i.canonical_sku) DESC",
            (item_id,),
        ).fetchall()
    found = []
    for row in rows:
        sku = row["canonical_sku"]
        if sku and re.search(rf"(?<![A-Za-z0-9]){re.escape(sku)}(?![A-Za-z0-9])", text):
            found.append(row)
        if len(found) >= limit:
            break
    return found


def save_comparison(sku: str, woo: dict | None, zoho: dict | None) -> None:
    aligned = 0
    if woo and zoho:
        aligned = 1 if woo.get("regular_price") == zoho.get("rate") and woo.get("name") == zoho.get("name") else 0
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO comparisons
              (canonical_sku, pulled_at, zoho_item_id, woo_product_id, zoho_json, woo_json, aligned)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sku,
                now(),
                (zoho or {}).get("item_id"),
                (woo or {}).get("id"),
                json.dumps(zoho) if zoho else None,
                json.dumps(woo) if woo else None,
                aligned,
            ),
        )
