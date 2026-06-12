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

## Outstanding for task 0.3 (authenticated, needs Application Password)

- Full per-product attribute assignments via `wc/v3/products` (closes the 147/302 gap)
- Pages, menus, widgets content; full plugin list (identify the exact Zoho connector,
  any invoice/tracking/B2B plugins)
- Where the finder PHP lives (child theme functions.php vs a mu-plugin vs custom plugin)
  — determines what we must re-implement vs can consult
- Customer/order counts (read-only sanity numbers for portal scoping)
