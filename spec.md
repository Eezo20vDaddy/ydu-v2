# YDU PARTS Website Rebuild — Product Spec (SSOT)

Created: 2026-06-12
Status: Draft v1 — approved scope from owner Q&A on 2026-06-12

## 1. Overview

Ground-up rebuild of **ydu.com.au** (YDU PARTS — VW, Audi & VAG specialist car parts,
Forrestdale WA). The current site runs the purchased KarPart ThemeForest theme with
Elementor and a stale bundled Slider Revolution. The rebuild replaces all of that with
clean, owned code. **Nothing from the KarPart theme, Elementor, or Slider Revolution is
reused.**

### Goals
1. Modern redesign around existing YDU PARTS branding (blue/white, existing logo).
2. Faithful replication of the custom **Make > Model > Submodel > Variant** vehicle
   finder, including its data.
3. Product attribute filtering preserved and combinable with vehicle fitment.
4. Faster site: no page-builder runtime, no RevSlider, static hero, Core Web Vitals pass.
5. Zero loss of products, orders, customers, SEO URLs, or payment capability.
6. **Side-by-side evaluation:** the rebuilt site runs on a parallel copy at
   **test.ydu.com.au** (owner-chosen) alongside the live store until the owner approves.
   Production keeps trading untouched the entire time. The subdomain itself is created
   at hosting level by the owner (or via the host's one-click staging feature).
7. **Zoho Inventory continuity:** the existing, working Zoho Inventory ↔ WooCommerce
   sync (stock → site, orders → Zoho, products/prices → site) must keep working
   unchanged through and after the rebuild.
8. **Customer portal:** restyled My Account area with order history + shipment
   tracking, downloadable PDF tax invoices, and trade/B2B (wholesale pricing) support.
9. **Pixel-perfect, mobile-first build quality** — owner-mandated bar; design variants
   approved from mockups before theme implementation starts (see docs/mockups/).

### Non-goals
- No platform migration (stays WordPress + WooCommerce on current LiteSpeed hosting).
- No catalog restructuring or repricing.
- No new commerce features beyond parity (wishlist/compare/quick-view are kept, not extended).

## 2. Constraints

- **Access:** wp-admin login only (no SFTP/SSH/cPanel). All code is built locally in
  this repo and delivered as installable zips via wp-admin upload. Server-side reads go
  through the WordPress REST API with an Application Password. Two acceptable access
  models (owner picks):
  - **Model A — temporary Administrator** (simplest): needed for installing the staging
    plugin and theme/plugin zips. Created fresh, deleted at cleanup.
  - **Model B — Shop Manager + guided installs**: agent gets a Shop Manager account
    (read products/orders/attributes via REST; cannot install or delete anything);
    owner personally performs the handful of install/activate clicks with step-by-step
    instructions.
- **Production write policy (hard rule):** until owner approval, the ONLY writes ever
  made to the production site are (1) installing the staging-clone plugin and creating
  the clone, and (2) at launch: uploading the theme + fitment plugin zips, creating the
  new pages/menus, and activating. **No task ever deletes or edits products, orders,
  customers, or any catalog data — on production or on the clone.** Old theme/plugin
  removal happens only after approval, behind a fresh full backup.
- **Side-by-side:** all build, data import, and QA happen on the staging clone, which
  runs in parallel with the live store for as long as the owner wants. Because live
  orders keep accruing during the evaluation period, launch is performed by installing
  the finished theme/plugin onto production — never by copying the staging database
  over production.
- **Catalog scale:** under 500 products (owner-confirmed) — taxonomy-based fitment is
  acceptable; no custom DB tables required at this scale.

## 3. Architecture decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Theme type | **Hybrid theme** (classic PHP base + theme.json + block patterns) | Officially endorsed pattern (WP Dev Blog "Bridging the gap"); classic Woo template overrides/hooks remain the reliable path for custom shop layouts in Woo 10.x |
| Cart/Checkout | **Block cart & checkout** (Woo default since 8.3) | Forward-compatible; WooPayments supports blocks; avoid legacy shortcode flows |
| Front-end interactivity | **WordPress Interactivity API** via wp-scripts script modules | First-party, stable since WP 6.5; right tool for cascading dropdowns. Heed WP 7.0 signal changes |
| Vehicle finder home | **Separate plugin `ydu-fitment`** (never in the theme) | Fitment data and endpoints must survive future theme swaps |
| Fitment data model | **As-is: flat WooCommerce attributes** (`pa_year_alt`, `pa_make`, `pa_model`, `pa_submodel`, `pa_variant`, `pa_engine_code`); cascade derived from term co-occurrence on products. **CEO decision 2026-06-13** after discovery showed the live site stores no tree | Zero data migration; owner's existing product-tagging workflow unchanged; all live `filter_*` URLs keep working (SEO parity). Known inherited quirk: multi-make parts can surface odd combos (already true on the live site) |
| Fitment endpoints | Custom REST routes `fitment/v1/*` (GET, cacheable, no nonce — public read-only data) | Faster than admin-ajax; edge-cacheable; fixes the live site's stale-nonce-in-cached-page failure class |
| Attribute filtering | Native Woo layered nav (`filter_*` params), `wc_product_attributes_lookup` enabled | Fitment IS attributes on this site; vehicle + spec filters combine natively |
| Data access | HPOS-safe CRUD APIs only (no direct postmeta queries) | HPOS sync-on-read off by default since Woo 10.7 |
| Build tooling | `@wordpress/scripts` (wp-scripts), npm | Canonical; handles script modules for Interactivity API |
| Local dev | wp-env if Docker/WSL2 available on this machine, else LocalWP | Verified at task 1.2 |

## 4. Branding & design

- Modern redesign (owner choice), preserving: YDU PARTS logo, blue/white palette,
  "VW, AUDI and VAG Specialists" tagline.
- **Approved design direction (CEO, 2026-06-12): Variant C — "Catalog Utility"**
  (`docs/mockups/variant-c-catalog-utility.html`): slim navy utility topbar, large
  combined search field, persistent vehicle-selector bar under the header with a
  "My Vehicle" chip, compact category tiles, dense product cards with prominent part
  numbers and stock badges — professional trade-counter feel. This mockup is the
  pixel-perfect build target for the theme.
- Trust signals on home page: Google 4.8★ rating, fast nationwide delivery, warranty,
  location (Unit 4/11 Weedon Road, Forrestdale WA 6112), phone 0409 853 662.
- Static hero section replaces Slider Revolution. Promo banner slots (e.g. battery sale,
  `welcome5` code) are editable block patterns, not a slider plugin.
- Fully responsive; design tokens centralized in `theme.json`.

## 5. Functional contract

### 5.1 Vehicle finder (parity-critical)
- Cascading selects: choosing a Make loads its Models; Model loads Submodels; Submodel
  loads Variants. Levels below the current selection are disabled until a parent is chosen.
- Submitting a selection navigates to the natively filtered catalog using the exact
  same URLs as the live site (`/shop/?filter_year_alt=…&filter_make=…&…`) — full URL
  and SEO parity.
- Selection persists across pages ("my vehicle") via localStorage + cookie; vehicle-aware
  UI renders client-side so full-page caching is never fragmented per user.
- A visible control clears/changes the selected vehicle.
- **No data migration:** the rebuild reads the same attribute terms in place (they live
  in the database, independent of theme/plugin code). The `ydu-fitment` plugin provides
  the cascade endpoints + widget; replies must match the live admin-ajax cascade
  (parity-verified against captures in `data/`).
- Finder widget appears on the home page hero and is reachable from the catalog.

### 5.2 Catalog & attributes
- Shop + category archives with attribute filter UI (layered nav); filters combine with
  an active vehicle selection (intersection, not union).
- All existing product attributes (`pa_*`) and their term assignments are preserved.
- Product cards: image, name, price, stock state, add-to-cart, wishlist, compare, quick view.

### 5.3 Commerce parity
- WooCommerce 10.x with WooPayments — checkout must complete a real test order on staging
  before launch. Google Listings & Ads and LiteSpeed Cache plugins are kept.
- Wishlist / Compare / Quick view: keep free WPClever plugins (maintained), restyled to theme.
- My Account, order tracking ("Check Your Order"), Contact, Find Us pages have content parity.
- **Zoho Inventory:** the existing connector (exact plugin/method identified in Phase 0
  discovery) is kept as-is on production. **On the test clone it MUST be disconnected/
  disabled before any test order is placed** — otherwise test orders would create real
  Zoho sales orders and stock movements. Post-launch verification includes one real
  order flowing into Zoho and a stock-level change flowing back.

### 5.5 Customer portal
- WooCommerce My Account restyled to the new theme: dashboard, order history with
  shipment tracking status, addresses, payment methods, account details.
- Downloadable PDF tax invoices per order (via a maintained plugin, e.g. PDF Invoices &
  Packing Slips, unless discovery finds one already installed — keep whatever Zoho/
  existing setup already generates if adequate).
- Trade/B2B: wholesale pricing tier(s) for workshop customers. Mechanism decided in
  discovery (check what exists today; otherwise evaluate B2BKing vs Wholesale Suite vs
  native roles + pricing rules — must be compatible with the Zoho price sync).

### 5.4 SEO & performance
- Permalink structure for products, categories, and pages is unchanged; any URL that must
  change gets a 301.
- Filtered catalog URLs (`filter_*`) keep the live site's canonical behaviour (parity).
- Lighthouse mobile performance ≥ 90 on home, category, and product pages (staging).

## 6. Launch criteria (go/no-go gate)

1. Staging QA checklist 100% pass: finder parity (spot-check ≥ 20 vehicles), attribute
   filters, test order via WooPayments, account login, emails, mobile layouts.
2. Owner approval of staging.
3. Fresh full backup taken immediately before production activation.
4. Post-launch within 1 hour: production test order, finder spot checks, 404 sweep of top
   50 URLs from the old sitemap.
5. Cleanup completed: KarPart (+child), Elementor, Slider Revolution removed; temporary
   admin account deleted.

## 7. Deliverables

- `themes/ydu/` — the hybrid theme (zip-installable)
- `plugins/ydu-fitment/` — vehicle finder plugin (zip-installable)
- `docs/discovery.md` — current-site audit & finder schema (Phase 0 output)
- `docs/launch-runbook.md` — staging→production switchover steps + rollback
