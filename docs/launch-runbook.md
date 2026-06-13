# YDU PARTS — Launch Runbook & QA Checklist

Last updated: 2026-06-13
Deliverables: `dist/ydu.zip` (theme), `dist/ydu-fitment.zip` (plugin)

This runbook covers (A) standing up the side-by-side test site, (B) the staging QA
checklist, and (C) the production launch + rollback. **Every production-affecting step is
CEO-gated.** Nothing here is executed without an explicit CEO go (spec §2, CLAUDE.md).

---

## A. Stand up test.ydu.com.au (Plans 0.4 / 5.1)

> Requires Administrator access for installs; the agent's `cocos` account is Shop Manager
> (read-only for our purposes), so the install clicks below are performed by the CEO or an
> admin, guided step-by-step.

1. **Create the subdomain / clone.** Use the host's one-click staging if available, else
   create the `test` subdomain and clone with WP Staging (Pro for subdomain target). The
   clone is a full copy of production at that moment.
2. **Make the clone safe — do these BEFORE anything else:**
   - [ ] **Disable the Zoho connector** (deactivate *Integration for WooCommerce and Zoho*
         + *…Zoho Pro*). **Non-negotiable** — a test order with Zoho live creates real Zoho
         sales orders + stock moves.
   - [ ] Put WooPayments / PayPal in **sandbox/test mode** (or disable live gateways).
   - [ ] Set the clone to **noindex** (Settings → Reading → Discourage search engines).
   - [ ] Confirm it's a separate database from production (WP Staging does this).
3. **Install the build:**
   - [ ] Plugins → Add New → Upload → `ydu-fitment.zip` → Activate.
   - [ ] Appearance → Themes → Add New → Upload → `ydu.zip` → Activate.
   - [ ] Deactivate the legacy **YDU WooCommerce Filter** plugin (replaced by ydu-fitment).
   - [ ] Tools → (WooCommerce) regenerate the **product attributes lookup table**.
   - [ ] Settings → Permalinks → Save (flush rewrite rules).
4. No fitment data import is needed — the cascade reads the existing `pa_*` attributes that
   are already in the cloned database.

---

## B. Staging QA checklist (must be 100% before launch — Plans 5.1)

Run on https://test.ydu.com.au. Tick every box; attach notes/screenshots for any fail.

### Finder (parity-critical)
- [ ] Vehicle bar shows on every page; Make populates with the 5 real makes.
- [ ] Selecting Make → Model → Submodel → Variant cascades; deeper selects enable in order.
- [ ] "Find Parts" redirects to `/shop/?filter_make=…&filter_model=…` and the catalogue
      narrows correctly. Spot-check **≥ 20 vehicles** against expectations.
- [ ] "My Vehicle" chip updates; selection persists across navigation and a new tab; Reset
      clears it.
- [ ] `fitment/v1/makes` (and models/submodels/variants) return JSON with cache headers.

### Catalogue & attributes
- [ ] Shop + category archives render Variant C cards (image/placeholder, part no, stock
      badge, price, add-to-cart).
- [ ] Attribute filtering narrows results; combining a vehicle filter with another attribute
      returns the intersection.
- [ ] Single product: gallery, price, add-to-cart, attributes table, **Fits these vehicles**
      panel, related products.
- [ ] Every product shows an image or the branded placeholder (never a broken slot).

### Commerce
- [ ] Add to cart works (AJAX); cart + checkout (block) render and are styled.
- [ ] **Place one sandbox test order end-to-end** (WooPayments test mode) — order completes,
      confirmation + email received.
- [ ] My Account: register/login, order history visible.

### Brand / responsive / quality
- [ ] Home, category, product, cart, account all correct at **375px and 1440px**; no
      horizontal scroll.
- [ ] Header search (category scope + keyword) returns product results.
- [ ] Mobile drawer opens/closes (hamburger, ESC, backdrop); focus trapped.
- [ ] Zero `elementor-*` / RevSlider / KarPart markup in page source.
- [ ] No JS console errors on any key page.

### CEO sign-off
- [ ] CEO has used the clone side-by-side and approves (Plans 5.2).

---

## C. Production launch (Plans 5.3 — highest gate, double confirmation)

> Executed only on explicit CEO go. **No deletions. No copying the staging DB over
> production. Catalogue / orders / customers are never edited.**

1. [ ] **Fresh full backup** of production (files + DB) — verified downloadable before any change.
2. [ ] Plugins → Upload `ydu-fitment.zip` → Activate. Deactivate legacy *YDU WooCommerce Filter*.
3. [ ] Appearance → Themes → Upload `ydu.zip` → Activate.
4. [ ] Tools → regenerate product attributes lookup table. Settings → Permalinks → Save.
5. [ ] Create/assign menus + any new pages (Home, Find Us, Contact) if not already present.
6. **Verify within 1 hour:**
   - [ ] Home, a category, a product, cart, checkout, My Account all load and look correct.
   - [ ] Finder cascades and filters on live data (spot-check 5 vehicles).
   - [ ] **Zoho round-trip:** place one real (small) order → confirm it appears in Zoho as a
         sales order; make a stock change in Zoho → confirm it syncs to the site.
   - [ ] 404 sweep of the top ~50 URLs from the old sitemap — 0 unintended 404s.
   - [ ] WooPayments back in **live** mode; a real payment authorises.

### Rollback (if launch verification fails)
- Appearance → Themes → reactivate **Karpart Child**; reactivate **YDU WooCommerce Filter**;
  deactivate `ydu` / `ydu-fitment`. Site returns to prior state (no data was changed). If
  anything looks wrong with data, restore the step-1 backup.

---

## D. Cleanup (Plans 5.4 — only after CEO confirms the new site is stable)
- [ ] Remove KarPart + Karpart Child, Elementor, UAE, Slider Revolution.
- [ ] Delete the temporary access: revoke the `claude-dev` Application Password (cocos →
      Application Passwords) and delete `memory/ydu-rest-api-credentials.md`.
- [ ] Remove the staging clone once no longer needed.
