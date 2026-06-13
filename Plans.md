# YDU PARTS Rebuild — Plans.md

Created: 2026-06-12
Contract: root [spec.md](spec.md) is the product contract; this file is the task ledger.
Precedence: spec.md > Plans.md.

---

## Phase 0: Discovery & Data Audit (read-only against production)

| Task | Description | DoD | Depends | Status |
|------|-------------|-----|---------|--------|
| 0.1 | Map the existing vehicle finder from the PUBLIC site: capture the dropdown's AJAX endpoints/payloads, crawl the full Make>Model>Submodel>Variant tree, infer the storage schema. No credentials needed. [tdd:skip:discovery-only] | `docs/discovery.md` documents endpoint shapes + `data/vehicles.json` holds the complete tree (counts per level recorded) | - | cc:done — KEY FINDING: no stored tree exists; fitment = flat `pa_*` attributes (6 levels incl. year + engine_code), hierarchy derived by co-occurrence via 5 admin-ajax actions (verified live); filtering = native Woo `filter_*` params. Full vocabulary + 147/302 product mappings exported; remaining product mappings covered by 0.3's authenticated export |
| 0.2 | Access setup per spec Model A or B: account created by owner, Application Password generated, REST verified. [tdd:skip:setup-only] | Authenticated `GET /wp-json/wp/v2/users/me` returns 200 | - | blocked (waiting on owner to create the account — see spec §2 access models) |
| 0.3 | Read-only export of production data: products (+attributes, categories, images list, vehicle assignments), pages, menus, widgets, plugin list, finder↔product mapping. Identify the Zoho Inventory connector (plugin/method) and any existing invoice / shipment-tracking / B2B-pricing plugins. [tdd:skip:discovery-only] | `data/` contains exports; product count matches wp-admin count; `docs/discovery.md` names the Zoho connector + portal-related plugins and documents finder↔product mapping source | 0.2 | cc:TODO |
| 0.4 | Create side-by-side clone at **test.ydu.com.au**: owner creates the subdomain in hosting (or uses host one-click staging); clone via host staging or WP Staging (Pro needed for subdomain target; free fallback = subdirectory). Only production write in Phases 0–4. [tdd:skip:ops-only] | https://test.ydu.com.au loads a working copy; checkout in sandbox mode (no live charges); **Zoho connector disabled on clone BEFORE any test order**; noindex enabled | 0.2 | cc:TODO |

## Phase 1: Local Environment & Theme Scaffold

| Task | Description | DoD | Depends | Status |
|------|-------------|-----|---------|--------|
| 1.1 | `git init` repo; scaffold hybrid theme `ydu`: style.css header, theme.json, functions.php with `add_theme_support('woocommerce')`, wp-scripts build pipeline. [tdd:skip:scaffold-only] | `npm run build` succeeds; theme activates on a clean local WP with zero PHP notices | - | cc:done [11fb48d] — build passes; activated on wp-env (WP 7.0/PHP 8.2): zero theme notices in debug.log, all PHP lint clean, home/search/404 render correctly; reviewer APPROVE |
| 1.2 | Local WP + WooCommerce 10.x environment (wp-env if Docker/WSL2 present, else LocalWP), seeded with exported real products and vehicle data. [tdd:skip:env-setup] | Local shop page renders ≥ 10 real YDU products with images and prices | 0.3, 1.1 | cc:done — wp-env up (WP 7.0/PHP 8.2/Woo, localhost:8888): all 302 real products + full attribute terms seeded, 282 images (20 products have no photo on live site — owner to supply); shop renders 16/page with prices+images. Note: node-DNS workaround required (c:\tmp\node-dns-fix.cjs via NODE_OPTIONS) |
| 1.3 | Design tokens + global shell per **approved Variant C mockup** (navy utility topbar, large search, persistent vehicle-selector bar with My Vehicle chip): theme.json palette & typography; responsive header, nav, footer. | Matches `docs/mockups/variant-c-catalog-utility.html` at 375px and 1440px; no horizontal scroll | 1.1 | cc:TODO |

## Phase 2: WooCommerce Templates

| Task | Description | DoD | Depends | Status |
|------|-------------|-----|---------|--------|
| 2.1 | Shop + category archives: product cards (image, name, price, stock, add-to-cart), pagination, sorting, attribute layered-nav sidebar with `wc_product_attributes_lookup` enabled. | Archive filtered by any `pa_*` attribute returns correct products locally; cards show all card elements | 1.2, 1.3 | cc:TODO |
| 2.2 | Single product template: gallery, price/stock, add-to-cart, attributes table, "fits these vehicles" list, related products. | Real product renders all sections; variable product switches price per variation | 2.1 | cc:TODO |
| 2.3 | Block cart & checkout pages styled to theme; WooPayments compatibility verified. | Test order completes locally (Woo test mode) and later on clone in sandbox; cart/checkout pass mobile layout check | 2.1 | cc:TODO |
| 2.4 | Restyle WPClever wishlist / compare / quick view to match theme. | All three function on product cards + single product; visual style matches theme tokens | 2.1 | cc:TODO |
| 2.5 | Customer portal: restyle My Account (dashboard, order history with shipment-tracking status, addresses, payment methods, account details) to theme. | Every My Account endpoint renders styled at 375px and 1440px; tracking status visible on a test order | 2.3 | cc:TODO |
| 2.6 | PDF tax invoices: keep/install maintained invoice plugin (per 0.3 findings), brand the template (logo, ABN, store details). | Test order produces a correct branded PDF invoice downloadable from My Account | 2.5 | cc:TODO |
| 2.7 | Trade/B2B wholesale pricing: implement mechanism chosen in discovery (existing setup, or B2BKing / Wholesale Suite / roles+rules) — must coexist with Zoho price sync. | Trade-role test user sees wholesale price; guest sees retail; Zoho price update doesn't clobber trade rules (verified on clone) | 2.1, 0.3 | cc:TODO |

## Phase 3: Vehicle Finder (`ydu-fitment` plugin)

| Task | Description | DoD | Depends | Status |
|------|-------------|-----|---------|--------|
| 3.1 | Plugin scaffold + cascade query layer over the EXISTING flat `pa_*` fitment attributes (CEO decision 2026-06-13: no migration, no new taxonomy): co-occurrence term lookups (year→make→model→submodel→variant→engine_code) with transient caching. [tdd:required] | PHPUnit tests pass on wp-env seeded with exported real data; cascade results for ≥ 10 sampled parent chains match live admin-ajax captures in `data/` | 0.1, 0.3, 1.2 | cc:TODO |
| 3.2 | REST endpoints `fitment/v1/{years,makes,models,submodels,variants,engine_codes}` — GET, parent-filtered, cacheable, no nonce. [tdd:required] | Endpoint unit tests pass incl. empty-parent and invalid-parent cases; responses send cache headers | 3.1 | cc:TODO |
| 3.3 | Cascading finder widget (Interactivity API): progressive enable per level, submit → native `/shop/?filter_*` URL identical to live site; persistent "my vehicle" via localStorage+cookie with client-side render (cache-safe; upgrade from live sessionStorage); clear/change control. | Selecting a vehicle filters catalog via live-identical filter_* URL; selection survives navigation + new tab; clearing restores full catalog | 3.2 | cc:TODO |
| 3.4 | Combined filtering verification: vehicle `filter_*` ∧ other attribute filters via native layered nav; enable `wc_product_attributes_lookup`; canonical behaviour parity with live. | Vehicle + attribute combined filter returns the intersection (verified against 5 hand-computed cases from `data/products-store-api.json`); lookup table active | 3.3, 2.1 | cc:TODO |

## Phase 4: Content, SEO & Performance

| Task | Description | DoD | Depends | Status |
|------|-------------|-----|---------|--------|
| 4.1 | Home page per **approved Variant C mockup**: hero promoting finder + trust stats, compact category tile grid, dense featured-product cards with part numbers/stock badges, editable promo banner patterns (replaces RevSlider). | Pixel-matches `docs/mockups/variant-c-catalog-utility.html` at 375/1440px; zero Elementor/RevSlider assets; promo banners editable as block patterns | 1.3, 3.3 | cc:TODO |
| 4.2 | Recreate static pages as clean block content: Contact, Find Us, Check Your Order, policies — full content parity, no Elementor markup. | Every published production page exists on clone; text-content diff reviewed; zero `elementor-*` classes in output | 0.3, 1.3 | cc:TODO |
| 4.3 | SEO parity: identical permalinks for products/categories/pages; 301 map for any changed URL; XML sitemap; meta titles/descriptions carried over. | Old-sitemap top-100 URL sweep on clone: 0 unintended 404s; metas spot-checked on 10 key pages | 4.2 | cc:TODO |
| 4.4 | Performance pass: image sizing/lazy-loading, LiteSpeed Cache config doc, script audit. | Lighthouse mobile performance ≥ 90 on clone home, category, and product pages | 4.1, 4.2 | cc:TODO |

## Phase 5: Side-by-Side Review & Launch

| Task | Description | DoD | Depends | Status |
|------|-------------|-----|---------|--------|
| 5.1 | Package `ydu` theme + `ydu-fitment` plugin zips; install on staging clone (fitment data already present in clone DB — no import step); full QA checklist (finder parity ≥ 20 vehicles, attribute filters, sandbox order, portal: tracking + PDF invoice + trade pricing, account login, emails, mobile). [tdd:skip:ops-only] | QA checklist in `docs/launch-runbook.md` 100% pass on clone (Zoho stays disabled on clone throughout) | Phase 2, Phase 3, Phase 4 | cc:TODO |
| 5.2 | Owner side-by-side evaluation period: owner uses the clone alongside the live store; feedback rounds applied to clone until sign-off. No time limit. [tdd:skip:review-only] | Owner gives explicit written go-ahead | 5.1 | cc:TODO |
| 5.3 | Production launch per runbook: fresh full backup → upload theme+plugin zips → create pages/menus → activate theme → verify (prod test order, finder spot checks, top-50 URL sweep, **Zoho round-trip: order appears in Zoho + stock change syncs back**). No import step — fitment data already lives in production attributes. NO deletions; NO database copy from clone; catalog/orders/customers untouched. [tdd:skip:ops-only] | All runbook verifications pass on production within 1 hour of activation incl. Zoho round-trip; rollback path (reactivate old theme) documented and untested-but-ready | 5.2 | cc:TODO |
| 5.4 | Cleanup (only after owner confirms stable): remove KarPart + child, Elementor, Slider Revolution; delete temporary access account; revoke Application Password. [tdd:skip:ops-only] | Old theme/plugins absent from wp-admin; temp account gone; site healthy after removal | 5.3 | cc:TODO |

---

## Priority matrix

- **Required:** 0.1–0.4, 1.1–1.3, 2.1–2.3, 2.5–2.7 (portal + Zoho continuity), 3.1–3.4, 4.2, 4.3, 5.1–5.3
- **Recommended:** 2.4 (wishlist/compare/quick-view restyle), 4.1 polish beyond parity, 4.4, 5.4
- **Optional:** multi-vehicle "My Garage" (owner deferred), fitment CSV admin importer UI
- **Rejected:** copying staging DB over production (live orders would be lost); reusing any KarPart/Elementor/RevSlider code (owner mandate)

## Code reuse audit

Empty greenfield repo — no prior code to reuse. Reuse happens via maintained third parties
instead of rebuilding: WooCommerce native cart/checkout/attributes, WPClever
wishlist/compare/quick-view, WP Staging for cloning. Verdict: all custom tasks **NEW**;
no common-promotion candidates (single-project scope).
