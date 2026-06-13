# Discovery — ydu.com.au Current Site (Task 0.1 / 0.3)

Updated: 2026-06-13
Status: Task 0.1 substantially complete (no credentials needed). Items marked **[needs 0.3]**
require the authenticated wc/v3 export once the Application Password arrives.

## Current stack (observed from public site)

| Layer | What's running |
|---|---|
| WordPress | 7.0 |
| WooCommerce | 10.8.1 (block-era, WooPayments, Google Listings & Ads) |
| Theme | KarPart 1.x + karpart-child (ThemeForest, WpOpal) |
| Page builder | Elementor 4.1.3 (header/footer via "hfe" — Elementor Header Footer plugin classes) |
| Slider | Slider Revolution 6.7.12 (bundled copy) |
| Caching | LiteSpeed Cache (JS combined/minified into one bundle) |
| Extras | WPClever woo-smart-{wishlist,compare,quick-view} |
| Catalog | **302 products** (Store API count, catalog_visibility=any) |

## The vehicle finder ("ydu-woo-filter") — custom code

Registered as script handle `ydu-woo-filter-script` (config object `ydu_filter_ajax` =
`{ ajax_url, nonce, shop_page_url }`). jQuery-based, lives inside the LiteSpeed JS bundle.

### Data model (the key finding)

**Fitment is stored as flat WooCommerce product attributes — there is no vehicle tree in
the database.** Six attribute taxonomies participate in the cascade:

| Level | Taxonomy | Terms (live counts) |
|---|---|---|
| 1 | `pa_year_alt` ("year") | 26 |
| 2 | `pa_make` | 5 — Audi, Cupra, Seat, Skoda, Volkswagen |
| 3 | `pa_model` | 62 |
| 4 | `pa_submodel` | 372 |
| 5 | `pa_variant` | 1,440 |
| 6 | `pa_engine_code` | 534 |

Also present (not in the cascade): `pa_engine_type` (710 terms), `pa_transmission` (12),
plus empty `pa_engine_capacity`, `pa_notes`, `pa_part`.

The "hierarchy" is **derived at request time from term co-occurrence on products**: e.g.
"models for Make X in Year Y" = distinct `pa_model` terms among products carrying both the
year and make terms. Nothing stores parent/child relationships explicitly.

### AJAX contract (verified live 2026-06-13)

`POST /wp-admin/admin-ajax.php`, params `action`, `_wpnonce` (from `ydu_filter_ajax.nonce`),
plus all ancestor term IDs:

| Action | Params |
|---|---|
| `ydu_get_makes_by_year` | `year_id` |
| `ydu_get_models_by_make` | `year_id, make_id` |
| `ydu_get_submodels_by_model` | `year_id, make_id, model_id` |
| `ydu_get_variants_by_submodel` | `year_id, make_id, model_id, submodel_id` |
| `ydu_get_engine_codes_by_variant` | `year_id, …, variant_id` |

Response: `{ "success": true, "data": [ { "id", "name", "slug" } ] }`.
Verified sample: year 2021 (id 702) → Audi, Cupra, Seat, Skoda, Volkswagen.

### Behaviour

- Cascade order: **Year → Make → Model → Submodel → Variant → Engine Code** (all six in
  the UI; the owner described it as Make>Model>Submodel>Variant — Year sits above and
  Engine Code below).
- Lower selects disabled until parents chosen; changing a parent clears+disables all
  descendants.
- Persistence: **sessionStorage** keys `yduwf_year|make|model|submodel|variant|engine_code`
  (per-tab, lost on browser close — our localStorage+cookie spec is an upgrade).
- Apply: redirects to `shop_page_url` with **native WooCommerce layered-nav params**:
  `/shop/?filter_year_alt=<slug>&filter_make=<slug>&filter_model=…&filter_submodel=…&filter_variant=…&filter_engine_code=…`
  → the product filtering itself is stock WooCommerce, only the cascade UI is custom.
- Reset button clears all sessionStorage keys.
- Also renders as a modal (`#filter-overlay`) from a "check your vehicle" button.

## Implications for the rebuild (decisions for cto-architect)

1. **Migration source is clean:** all six levels are ordinary attribute terms; per-product
   assignments are ordinary term relationships. The importer (task 3.1) maps these into
   the plugin's data model. Term vocabulary already exported (`data/attribute-terms.json`).
2. **Spec §3 decision point:** spec currently says fitment moves to a hierarchical
   `vehicle` taxonomy and stays OUT of `pa_*`. The live data is flat + co-occurrence-derived.
   Two faithful-replication options: (a) keep flat attributes + replicate co-occurrence
   endpoints in `fitment/v1` (zero data migration, native filter_* URLs keep working —
   strong SEO/parity argument), or (b) build the explicit tree (cleaner, but must be
   generated from co-occurrence and risks materialising false combinations for
   multi-fit products). **Recommendation: (a) — replicate the flat model; revisit spec §3.**
3. **Multi-fit caveat:** a product fitting multiple vehicles carries multiple terms per
   level; co-occurrence can imply combinations that don't exist (e.g. a part on both a
   VW Golf and an Audi A3 makes "Audi Golf" reachable). The live site already has this
   trait — parity means replicating it, not fixing it silently. Flag to owner later.
4. **Nonce/caching:** the AJAX requires a nonce embedded in cached pages — nonces expire
   (~24h) while LiteSpeed caches the page; the rebuild's public GET `fitment/v1` routes
   without nonces (public read-only data) avoid this whole failure class.

## Exported data (in `data/`)

| File | Contents | Completeness |
|---|---|---|
| `attribute-terms.json` | Every term (id/name/slug/count) for all 8 fitment-related attributes | **Complete** |
| `products-store-api.json` | All 302 products: name, sku, prices, stock, categories, images, attributes | Attributes only on 147 products (Store API hides non-visible attributes) **[needs 0.3]** |
| `vehicles.json` | Meta + AJAX contract + per-product fitment term IDs (147 products) | Provisional **[needs 0.3]** |

## Task 0.3 — authenticated export (DONE 2026-06-13, user `cocos`/shop_manager)

Exports in `data/export/`: `products-wc-v3.json` (**317** products incl. drafts, 156 with
attributes), `pages.json` (13), `menus.json` (2) + `menu-items.json` (19),
`product-categories.json` (21), `settings-general.json`, `shipping-zones.json`,
`payment-gateways.json`, `system-status.json`. (`wp/v2/plugins` 403 for shop_manager —
plugin list recovered from system status instead.)

### Active plugins (production, from system status)

| Plugin | Version | Disposition in rebuild |
|---|---|---|
| **YDU WooCommerce Filter** | 2.0 | **REPLACE** with `ydu-fitment` (this is the custom finder — it IS a standalone plugin, confirming our architecture) |
| Integration for WooCommerce and Zoho **Pro** | 1.5.8 | **KEEP untouched** — Zoho connector (disable on clone) |
| Integration for WooCommerce and Zoho | 1.6.2 | **KEEP untouched** — Zoho connector (paired) |
| Print Invoice & Delivery Notes for WooCommerce | 7.1.2 | **KEEP + brand** — covers task 2.6 (PDF invoices already exist; no new plugin needed) |
| WPC Smart Wishlist / Compare / Quick View | 6.0.4 / 6.5.7 / 4.3.2 | KEEP + restyle (task 2.4) |
| Variation Swatches for WooCommerce | 2.3.0 | KEEP — variation UI |
| WooPayments / PayPal Payments | 10.8.0 / 4.0.4 | KEEP — payments |
| LiteSpeed Cache | 7.8.1 | KEEP — caching |
| FOX Currency Switcher Pro | 1.4.8 | KEEP — multi-currency |
| Google / Meta / Pinterest / TikTok for WooCommerce, Mailchimp (x2) | — | KEEP — marketing feeds |
| Contact Form 7 | 6.1.6 | KEEP — contact forms |
| Theme My Login | 7.1.14 | KEEP/evaluate — front-end login (My Account portal task 2.5) |
| Product Import Export for WooCommerce | 2.6.4 | KEEP — used for catalog import (likely Zoho-adjacent) |
| WP Armour Honeypot / Limit Login Attempts | 2.3.04 / 3.2.4 | KEEP — login security (note: blocks scripted login; use real browser) |
| **Elementor + UAE + Slider Revolution** | 4.1.3 / 2.8.8 / 6.7.12 | **REMOVE** at cleanup (task 5.4) — owner mandate |

Theme: **Karpart Child v1.0.8** (parent KarPart). Env: WC 10.8.1, WP 7.0, **PHP 8.1.34**
(⇒ target PHP 8.1 compatibility, not just 8.2). HPOS not enabled (legacy post storage) —
still use CRUD APIs per spec.

### Scope deltas this export revealed

1. **Task 2.6 (PDF invoices):** already solved by *Print Invoice & Delivery Notes* — rebuild
   just brands its template. No new plugin / purchase.
2. **Task 2.7 (trade/B2B pricing): NET-NEW — nothing on the live site provides it today.**
   No B2B/wholesale plugin is installed. This is new functionality the owner requested, not
   parity. **Autonomous decision (no paid plugin without approval):** implement native
   role-based wholesale pricing — a `trade` customer role + role-priced display, applied via
   Woo price hooks, compatible with the Zoho price sync (Zoho writes regular/sale price;
   trade pricing is a computed display layer, never overwrites stored price). Owner can
   later swap in B2BKing/Wholesale Suite if they want richer features — flagged for review.
3. **My Account portal (task 2.5):** *Theme My Login* is active — evaluate whether to keep it
   or use native Woo My Account; restyle whichever.
4. Finder confirmed as plugin `YDU WooCommerce Filter v2.0` → clean replacement target.
