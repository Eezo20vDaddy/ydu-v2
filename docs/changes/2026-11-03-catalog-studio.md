# Catalog Studio — local authoring, then Zoho and WordPress

Created: 2026-11-03
Status: **Proposal — not in spec.md, not in Plans.md.** Theme launch (Plans phases 0–5) is unchanged until the CEO accepts this workstream.
Spec delta: proposed below. Not applied.

## CEO Requirement (Verbatim)

> we need a comprehensive plan for me to be able to import and export items into the catalog. we work on VAG Group car parts adn the part number situations are hectic.
>
> I need an interface that will allow me to create the catalog item off system so i can fine tune the entire product using ai assistance, then have it sync to Zoho and Wordpress.
>
> so i dont know which is master and which is slave between zoho and wordpress, there's also a multitude of actions that need to take place, ie syncing to meta and syncing to google. I need a separate local website to setup the catalog and have it push to both Zoho and Wordpress. M

**Coordinator (2026-11-03):** The last character is a cut-off "M". Nothing after it was received. This plan covers only the sentences above.

> 1. I need to be able to paste in ebay links, and from those links you will need to retrieve the photos, list of supported cars, list of superceded part number etc.
> 2. i also need the ai to research the part number and come up with all the variations of the part number (superceded part numbers, alternate manufacturer part numbers becuase VW number may be different to audi and porsche, skoda etc). This item needs to be able to pull down pictures and links from the evidence its providing.
> 3. We need to auto generate titles to be SEO optimised so that when a customer searches google with any of the variations of a single part number, our store comes up first.
> 4. This tool needs the ability to convert the images from the ebay format to the zoho format (png)
> 5. This tool needs to allow me to select the hero picture
>
> all of the above needs to be able to be done on a single screen, so layout is important.

**Coordinator (2026-11-03, follow-up):** Points 1–5 are in the screen, evidence, image, and title sections below. The earlier line that AI may only repeat a number you already typed is replaced by this follow-up: AI may propose cross-brand and superseded numbers, and each proposal must bring its link and its picture. A number with no evidence cannot be ticked, and an unticked number cannot publish.

> we need to make sure this " so the plan puts the variations on the page and keeps the title short." doesnt catch us out with google search. we must be on page 1 of google.
> if a user searches for 03L198119F as we stock 03L198119B (which is the same part) we still need to show up on page 1.

> does the ebay api work for anyone, or is it a subscription thing? I will look manually at a page and just post the item url.

**Coordinator (2026-11-03, follow-up 2):** `03L198119F` and `03L198119B` are different search strings. A short title that only carries B will miss a search for F. The title now uses the full 150 characters, and every distinct ticked number is placed in the title until that cap is full, then in the first sentence of the description. Page 1 is the acceptance check after Google has indexed the page. It is not something the software can force on its own.

eBay’s developer program is free, not a subscription. Daily work is pasting the item URL. A key is created once on this PC.

> The point is we need to have both 03L198119F and 03L198119B embedded somewhere on the page that shopping and search crawls.

**Coordinator (2026-11-03, follow-up 3):** Every ticked distinct number is plain text in the product HTML Google Search crawls, and the same plain text is in the title or description the Google plugin sends to Shopping. Publish is refused if either string is missing from either place.

> if you crawl here:
> https://www.ebay.com.au/itm/137092930759?_skw=03L198119F&itmmeta=01M6FPE2C755G62EQQM2EHKGCF&hash=item1feb601cc7:g:TPkAAeSw20xpp8eh&itmprp=enc%3AAQALAAAA0CHNgUiiE%2FjQhlDTaMiAde8ds5qiLvgHFMOua0z7HGLzC7GQdTemGm1QhGiDKZSJnv65Dhc5txzdKgowAszxAw6vz1LL1jspudEQDxEs5II06I2ykwIevwWDugGBd5BVw2zj3ySGqpLw6lgAB9zjaX9iv1SbaIM7eVRsCLwuIzygi%2FsjOs8yuv%2BUhbIow81eDybhNScnfX9WBtQAgJ7a4yoi%2FK3MVtH0j8Win8px54SZh%2BGOZBRdTbZhmot02HKxCB3ZWiIxLH0Q4nLfqtdW3Go%3D%7Ctkp%3ABk9SR5CnuPazaA
> you will see a table that lists all the cars that fit this part see attached and we need to walk through each page and capture each unique item.

**Coordinator (2026-11-03, follow-up 4):** Item `137092930759` states 38 compatible vehicles and the table is split across page 1 and page 2. The studio stores each unique row from every page. The seven columns on that listing are one table version, not the shape of every part.

> the number of columns and the content will vary by part. we need a way of understanding which version of the table is being imported adn extract accordingly.
> if a new version is on a given page that hasnt been processed, ie no template, then we set it up there an then at run time and store the template processing on file or in a db somewhere.

**Coordinator (2026-11-03, follow-up 5):** A table version is the ordered header row. A known header uses its saved template. An unknown header pauses on that page, you map the columns once, and that mapping is stored in the studio database and in a template file. Later pages and later parts with the same header use it without asking again.

> confirm that the parts will be mapped back to our vehicle catalog. if there's a new vehicle in the ebay listing that we dont have listed on our site, i need to approve this in the UI, highlight the offending vehicle and just add a confirm. also allow me to delete any vehicles that i dont want listed.
>
> Make sure that we have a seperate page in the app that configures the vehicle catalog. we also need to rearrange the cascade order.
> Needs to be year, make, model, submodel, variant, engine code. This is just the reference data for the vehicle cataloy. how the dropdowns behave in the front end i will sort out in another session.

**Coordinator (2026-11-03, follow-up 6):** Each extracted vehicle is matched to the studio vehicle catalog. A path that is not already there is highlighted on the part screen. Confirm adds that path to the catalog. Delete removes it from the part. The catalog itself is a separate page, ordered year, make, model, submodel, variant, engine code. Shop dropdown behaviour is unchanged in this workstream.

> we also need another page which is a comparison of the contents of the zoho item against the wordpress item. we need to pull and compare all the metadata in both systems to ensure alignment. the SKU is the primary key

> side my side comparison

**Coordinator (2026-11-03, follow-up 7):** A separate page pulls the Zoho item and the WordPress product for one SKU and shows them side by side. SKU is the only join key. Every field from both sides is listed. The page does not write to either system.

> i need a chat window as well to talk to the ai assistant about the car parts. connect to my OpenAi account which i can load into the .env file

**Coordinator (2026-11-03, follow-up 8):** The part screen has a chat window under the photos, evidence, and item. It talks to the OpenAI account in `.env` (`OPENAI_API_KEY`, optional `OPENAI_MODEL`). The key is not shown on the page and is not written into the studio database. The assistant can see the open part. It does not invent a part number as fact, and it does not write to the shop.

## Answer

Neither Zoho nor WordPress is the place to build a VAG part. **The local Catalog Studio is the authoring master.** Zoho stays the stock, order, and invoice system. WordPress stays the shop. Google and Meta stay downstream of WordPress, through the plugins already on the live site.

You import the current catalog into the studio, fine-tune one item (with AI only where you accept the draft), then publish. Publish writes the shop content to WordPress and the stocked item to Zoho. It never writes stock quantity. It never talks to Google or Meta itself.

## Who owns what

| Concern | Master | What the others do |
|---|---|---|
| Part numbers, supersessions, fitment, titles, descriptions, images, categories, intended shelf price | Catalog Studio (this machine only) | Sends a copy on publish |
| Stock on hand | Zoho Inventory | Existing connector may update Woo stock. Studio shows stock read-only and never sends a quantity |
| Orders, invoices, edited invoice line prices, trade "last price paid" | Zoho | Woo takes the order. Trade price stays in `ydu_trade_prices` and never replaces shelf price (spec §5.5) |
| Shop pages, cart, checkout, SEO URLs, `filter_*` fitment URLs | WordPress / WooCommerce | Receives merchandising fields only |
| Google, Meta, Pinterest, TikTok | WooCommerce channel plugins already installed | Studio only shows whether the Woo product has the fields those plugins need |

### Why not Zoho as the editor

Zoho Inventory stores one item: name, one SKU, a rate, stock. It does not store a VW/Audi/Skoda/Seat supersession chain or the six fitment levels on the shop (`pa_year_alt`, `pa_make`, `pa_model`, `pa_submodel`, `pa_variant`, `pa_engine_code`). Official Zoho WooCommerce integration copies **items from Woo into Zoho**, then pushes **stock from Zoho back to Woo** ([Zoho Inventory WooCommerce help](https://www.zoho.com/us/inventory/help/integrations/woo-commerce.html)). That is the opposite of an authoring master.

### Why not WordPress as the editor

The shop is the storefront. The live connector is CRM Perks **Integration for WooCommerce and Zoho** 1.6.2 plus **Pro** 1.5.8 (`docs/discovery.md`). That plugin's public docs push Woo orders and products **into** Zoho, with a configurable field map ([plugin page](https://wordpress.org/plugins/woo-zoho/)). Spec §1 says the working sync is stock and prices **toward** the site and orders **toward** Zoho. Both statements can be true only for the feeds actually configured. **Those feeds are not in this repo.** Until a read-only export of WooCommerce → Zoho Feeds exists, nobody should add a second writer.

### Price, stated as a target

Shelf price is authored in the studio. On publish it is written to Woo `regular_price` and Zoho item `rate` as the same number. After that, the product feed must not keep copying price in either direction. Order line prices and trade last-price stay separate. Sale price is not invented by the studio in v1.

This target is blocked until the feed export says what the connector does today. If a feed already owns price, the CEO turns that mapping off before the first live publish. That is a change to the connector, which spec §5.3 currently says to leave untouched.

## Part numbers

One stocked item. Many numbers. The number you invoice stays the SKU you already have. Import does not renumber the 317 products.

| Field | Rule |
|---|---|
| Canonical SKU | Exact Woo SKU and exact Zoho SKU. Case-sensitive. Never rewritten by a publish |
| Alias | A number customers or suppliers use for that same stocked item |
| Kind | `oem`, `aftermarket`, `superseded`, `replaces`, `barcode` |
| Brand | Volkswagen, Audi, Porsche, Skoda, Seat, Cupra, or the aftermarket brand |
| Raw | As printed, spaces and dashes kept |
| Normalized | Uppercase, spaces and hyphens removed. `06L 145 612 L` and `06L145612L` are the same key |

Rules:

- The same normalized number is not attached to two stocked items. The studio flags the clash. It does not merge by itself.
- A superseded number stays on the item so search still finds it. A second stock item is created only when you still stock both the old and the new part.
- A superseded number stays searchable. AI may propose more numbers (VW, Audi, Porsche, Skoda, Seat, Cupra, and the aftermarket brand). Every proposed number must show the link it came from and a picture saved from that evidence. You tick it. Unticked rows and rows with no link or no picture do not publish.
- Locked dealer catalogs (ETKA, Partslink24, and anything behind a login) are not opened or bypassed. If the evidence is a public page, the studio stores the link and downloads the public image. If it is behind a login, you type the number and attach a photo yourself.

Fitment stays the shop's flat attributes. The studio stores real rows (year, make, model, submodel, variant, engine code). Publish compiles those rows into the existing `pa_*` terms. No new taxonomy (CEO decision 2026-06-13, spec §3). Known limit: a part that fits two makes can leak odd combinations in the finder. That leak already exists on the live site. The studio must show it before publish. It does not fix it by inventing a tree.

## One screen

All five jobs happen on one page. No wizard and no second page. The working size is a wide desktop window (1440px wide, 900px tall): the paste bar, the photos, the evidence, the item, and the publish bar are all visible together. On a narrower window the columns stack on the same page.

```
+------------------------------------------------------------------+
| eBay link [........................] [Pull]   SKU ____  Price __ |
+------------------+------------------------+----------------------+
| PHOTOS           | EVIDENCE               | THE ITEM             |
| large hero       | Cars from the listing  | Numbers, each with   |
| filmstrip        | Superseded numbers     |   link, picture, tick|
| click = hero     | AI cross-brand numbers | Fitment rows         |
| PNG ready / not  | each row: number,      | SEO title, editable  |
|                  | brand, link, picture   | Short description    |
+------------------+------------------------+----------------------+
| Hero set · PNG under 7 MB · unticked rows blocked     [Publish] |
+------------------------------------------------------------------+
```

The hero is the picture you click. That click is the only way a photo becomes the Zoho primary image and the Woo featured image. The other photos you keep are the gallery.

A chat window sits on the same page, under those three columns. You talk to it about the open part. It uses the OpenAI key in `.env` at the project root. Copy `.env.example` to `.env` and put the key on the `OPENAI_API_KEY` line. The studio reads that file when you send a message. The reply stays in the window for that part.

### eBay link

You paste an `ebay.com.au` or `ebay.com` item link. The studio reads the item id from the link and calls eBay's official Browse API (`getItemByLegacyId`, `fieldgroups=PRODUCT`, marketplace `EBAY_AU` for `.com.au`). That call returns the photos, the item specifics, the description, and catalog identities when eBay has them ([Browse getItem](https://developer.ebay.com/api-docs/buy/browse/resources/item/methods/getItem)).

What that call does **not** return is the car table in your screenshot. eBay's `checkCompatibility` only answers yes or no for one car you already name.

The car table on item `137092930759` says **38 vehicles** and is split into **page 1 and page 2**. Columns, in order: Make, Model, Year, Submodel, Variant, Engine, Notes. Page 1 is Volkswagen Amarok, years 2022 down through 2013. The Variant cell carries the drivetrain and the engine codes (`CNEA,CSHA`, `CNFB`). The Engine cell is the size and power (`1968cc 132kW (Diesel)`), which is not the engine code. Notes is its own column and is kept even when blank.

The studio walks every page of that table. A row is unique on all seven cells together, so the 2022 Amarok and the 2013 Amarok stay as two rows. It stops when the number of unique rows equals the heading ("38 vehicle(s)"), or when the pager has no further page. If those two numbers disagree, fitment stays incomplete and the gap is shown. It does not invent a vehicle to close the gap.

Official `GetItem` with `IncludeItemCompatibilityList` is tried first, because that response is the same table without the on-screen pager. eBay's Trading API release of 6 Oct 2026 says that outside the US and Canada this list is returned to the seller, or to someone the seller has authorised. This listing is on ebay.com.au. When that call returns only the count, the studio follows the listing's own compatibility pages until the unique rows equal 38. Page 2 is required for this fixture. The first screen is not the finished list.

Those rows are extracted by a **table template**, not by a fixed seven-column parser. The Amarok listing is template number one, once you have mapped it. Another part may have fewer columns, different names, or the engine code in a different cell. The version of a table is its header row, in order, with the letter case ignored. `Make, Model, Year, Submodel, Variant, Engine, Notes` is one version. `Year, Make, Model, Trim, Engine` is another.

On each page the studio reads the header and looks up that version:

- A saved template extracts every row on that page, then the walk continues.
- No template: the walk pauses on that page. The screen shows the header and three sample rows. You point each column at a shop field (year, make, model, submodel, variant, engine code, engine display, notes), or you mark it “keep only” or “ignore”. If one cell holds engine codes inside other text, you mark that column as the code source. You save. The rest of the pages with that same header use the new template immediately.
- A later page whose header is a version not yet saved pauses again, even in the middle of the same listing.

The mapping is stored in the studio database and written to `data/table-templates.json` at the same time. The file is the copy you can move with the studio. The database is what the screen reads. Every raw cell is kept on the row, so a mapping you correct later can be run again without fetching the listing a second time. Fitment from an unsaved mapping does not publish.

Item specifics named like superseded part number are stored as alias candidates with that listing as the evidence link, and the listing photo as the evidence picture.

You look at the listing yourself and paste that item URL. That is the whole daily step. The studio reads the item id out of the URL.

eBay’s Developers Program is free. It is not a monthly subscription. Membership includes a free tier of 5,000 API calls a day ([eBay Partner Network](https://partnernetwork.ebay.com/solutions/step-4-optimizing-and-automating)). One call per listing is enough for this screen, so a day’s catalog work stays inside that tier. You create one application at [developer.ebay.com](https://developer.ebay.com/) and the keys stay on this PC. There is no per-listing login and no shop plugin.

The free call returns live listings. A finished auction, or an auction that already has a bid, can come back empty. Sold-price history is a different eBay API and is not part of this tool. Photos and item specifics still come from the Browse API. The car rows come from the compatibility table, page by page, as above.

### Vehicle catalog

Every extracted vehicle is matched to the studio’s vehicle catalog. The catalog is the reference list, seeded from the vehicles already on the shop. A row matches when its year, make, model, submodel, variant, and engine code are already in that list. Those six fields are the same six shop attributes (`pa_year_alt`, `pa_make`, `pa_model`, `pa_submodel`, `pa_variant`, `pa_engine_code`).

On the part screen, a vehicle that is not in the catalog is highlighted. The only action that adds it is Confirm. Confirm writes that path into the catalog and links the part row to it. Delete on that same row takes the vehicle off this part. A deleted row is not published and is not added to the catalog.

The catalog has its own page, separate from the part screen. The reference order on that page is:

1. Year
2. Make
3. Model
4. Submodel
5. Variant
6. Engine code

That order is the reference data only. How the shop dropdowns behave stays as it is until a later session. This workstream does not change the finder.

Publish sends only catalog vehicles that are still on the part. A highlighted row with no Confirm is not written to the shop.

### Zoho and WordPress, side by side

A separate page pulls one Zoho item and one WordPress product and places them side by side. The join key is the SKU, exact and case-sensitive. There is no match on name.

The left column is Zoho. The right column is WordPress. Each row is one field. A field that exists on both sides shows both values. A field that exists on only one side shows a blank on the other side. Equal values are marked aligned. Different values are marked not aligned. Stock and price are shown the same way as every other field. This page does not copy a value across, and it does not publish.

The list above the pair is every SKU in either system. A SKU present in only one system is a row of its own, with the missing side empty. Opening a SKU loads both records in full, including WordPress product meta and Zoho custom fields, not a short list chosen in advance. Images are compared by count and by file name. Fitment attributes on the WordPress side are listed with the Zoho fields beside them.

The first pulls are read-only: local WordPress, and a Zoho sandbox once that connection exists. A live Zoho pull waits on the same approval as any other live Zoho call.

### AI research and evidence

You give it the stocked number. It proposes the other numbers: superseded, and the VW / Audi / Porsche / Skoda / Seat / Cupra equivalents. Each proposal is a row on this same screen:

- the number and the brand
- the page it came from (the link stays visible)
- the picture downloaded from that evidence
- a tick, off until you turn it on

A row missing the link or the picture stays blocked. The studio does not log into ETKA, Partslink24, or any other paid catalog, and it does not bypass a login. Public pages only. You can still type a number from a catalog you looked up yourself and attach one of the photos already on the screen.

### Numbers Google can crawl

`03L198119B` and `03L198119F` are both written on the product as plain text. Search crawls the page. Shopping crawls the product feed the Google plugin builds from that same page. If either number is only in a photo, a script, or the studio, it does not count.

Publish checks two copies:

- The product HTML contains every ticked distinct number as text.
- The title or the description that Google Listings & Ads sends contains those same strings.

Worked page: the title reads `Oil cooler 03L198119B replaces 03L198119F`. The first line under it repeats any ticked number that did not fit in the 150-character title. The feed receives that title and that line. One product, one address.

The screen preview lists each ticked number and marks it “on the page” or “missing” before you can publish. Spacing of one number (`03L198119F` and `03L 198 119 F`) still counts as that number. A different ending does not.

### Photos to PNG

eBay serves JPEG or WebP. Zoho Inventory accepts gif, png, jpeg, jpg, bmp, and webp, up to 7 MB per file, and can set the primary image on upload ([Zoho item image](https://www.zoho.com/inventory/api/v1/items/)). You asked for PNG. The studio converts the file you selected as hero, and any gallery photo you keep, to PNG with PHP GD (already on the local WordPress PHP — no new image package). If the PNG is over 7 MB it is scaled down until it is under 7 MB and still PNG. The publish bar shows "PNG ready" or the reason it is not. Zoho receives the hero with `update_primary_image` set. Woo receives the same hero as the featured image.

A photo from someone else's listing is stored as evidence either way. It is sent to Zoho and Woo only after you tick "I can use this photo" on that picture. Your own listing photos are the normal case for that tick.

## What publish does

One confirmed action, in order, idempotent, matched on SKU:

1. Validate: SKU present, at least one number, shelf price, category, a hero PNG under 7 MB with the rights tick, every publishing number ticked and holding a link and a picture, an SEO title of 150 characters or fewer, and either fitment rows or an explicit universal-part flag.
2. Upsert the Zoho item: name, SKU, rate, short description. Upload the hero PNG as the primary image and kept PNGs as the rest. Do not send stock, reorder level, or opening stock.
3. Upsert the Woo product: title and description that together contain every ticked distinct number as plain text, images, categories, brand, the stocked number as MPN, GTIN only if you entered one, and compiled `pa_*` terms. Do not send stock or sale price. The same title and description are what the Google plugin gives Shopping.
4. Save a receipt: Zoho item id, Woo product id, field hashes, time, error text.
5. Stop. Google Listings & Ads and Meta for WooCommerce, already on the live shop, read the Woo product. The studio shows a readiness line: image, price, availability, brand, and either a GTIN or MPN plus brand. VAG parts often have no barcode. Missing GTIN is allowed when MPN and brand are set. The studio does not call Google or Meta.

First publishes go to **local wp-env** and, for Zoho, a **sandbox organisation**. Production ydu.com.au and test.ydu.com.au do not get this app installed. The theme zip pipeline (`tools/package-zips.ps1`) does not include it.

## Import and export

| Direction | v1 |
|---|---|
| In | Woo product export (WebToffee Product Import Export 2.6.4 is already on the live site) plus, once OAuth exists, Zoho items. Match on SKU. Unmatched rows are a report, not a silent create |
| Out | Studio JSON (the copy you can re-import) and a Woo-shaped CSV the existing importer can load if the API path is down |
| Not in v1 | A direct Google or Meta file. Those channels already have plugins |

`data/export/products-wc-v3.json` is the June 2026 export (317 products). C0 does not copy it. C0 writes a new file from a new GET and records the pull time.

## Database Changes

No WordPress tables. No new `pa_*` taxonomy. No Alembic. No change to `ydu_trade_prices`.

New **local SQLite** file, on this machine only, not deployed:

| Table | Purpose | Columns |
|---|---|---|
| `items` | One stocked sellable | `id` PK; `canonical_sku` unique not null; `name`; `seo_title`; `primary_alias_id` nullable FK; `short_description`; `long_description`; `shelf_price` numeric; `brand`; `mpn`; `gtin` nullable; `woo_product_id` nullable; `zoho_item_id` nullable; `status` (`draft`, `ready`, `published`, `error`); `universal_part` integer default 0; `updated_at` |
| `aliases` | Every other number | `id` PK; `item_id` FK; `kind`; `brand`; `raw`; `normalized`; `source` (`import`, `user`, `ebay`, `ai`); `evidence_url`; `evidence_media_id` nullable FK; `confirmed` integer; unique (`item_id`, `kind`, `brand`, `normalized`) |
| `table_templates` | One compatibility-table version | `id` PK; `fingerprint` unique (ordered headers, lowercased, joined); `label`; `created_at`; `sample_headers`; `sample_row` |
| `template_columns` | How that version is extracted | `id` PK; `template_id` FK; `source_header`; `position` integer; `target` (`year`, `make`, `model`, `submodel`, `variant`, `engine_code`, `engine_display`, `notes`, `raw_only`, `ignore`); `extract` (`whole_cell`, `engine_codes_inside`) |
| `vehicles` | Reference catalog. One path | `id` PK; `year`; `make`; `model`; `submodel`; `variant`; `engine_code`. Unique on those six. Display order is year, then make, then model, then submodel, then variant, then engine code |
| `fitment_rows` | One vehicle from one page, after the template, then matched to `vehicles` | `id` PK; `item_id` FK; `template_id` FK; `vehicle_id` nullable FK; `match_status` (`matched`, `new`, `deleted`); `page_number`; `raw_json`; `year`; `make`; `model`; `submodel`; `variant`; `engine_display`; `engine_code`; `notes`; `source` (`ebay-table`, `user`, `ai`); `evidence_url`; `ebay_item_id`; `confirmed` integer. Unique on (`item_id`, `template_id`, hash of `raw_json`). `new` is the highlighted row. Confirm sets `vehicle_id` and `matched`. Delete sets `deleted` |
| `sources` | One pasted eBay listing | `id` PK; `item_id` FK; `url`; `ebay_legacy_id`; `fetched_at`; `raw_path` |
| `media` | Local image files | `id` PK; `item_id` FK; `source_url`; `original_path`; `png_path`; `bytes` integer; `is_hero` integer default 0; `rights_confirmed` integer default 0; `role` (`hero`, `gallery`, `evidence`) |
| `comparisons` | One side-by-side pull for one SKU | `id` PK; `canonical_sku`; `pulled_at`; `zoho_item_id` nullable; `woo_product_id` nullable; `zoho_json`; `woo_json`; `aligned` integer. No write to Zoho or WordPress |
| `receipts` | One row per publish attempt | `id` PK; `item_id` FK; `target` (`woo-local`, `woo-live`, `zoho-sandbox`, `zoho-live`); `ok` integer; `request_hash`; `response_excerpt`; `created_at` |

Indexes: `items.canonical_sku`; `aliases.normalized`; `receipts.item_id`; one hero per item (only one `media.is_hero = 1` per `item_id`).

`primary_alias_id` points at the number that leads the SEO title. Alias kind and media role stay the closed lists above. No WordPress column is added.

JSONB / vocab: none in WordPress. Studio status and alias kind are the closed lists above.

## Reuse audit

Source: [CTO architect](6811cad9-d34a-4713-b3d6-c66c23f7bca7), read-only, 2026-11-03. LevelUpAI shared packages are not this repo. Memory store was not searched (`not_observed`).

| Capability | Verdict | Evidence |
|---|---|---|
| Authoring UI | NEW | No admin editor. Closest: `tools/seed-local-products.php` |
| Alias / supersession | NEW | SKU is display-only on the product card |
| Fitment rows → `pa_*` | EXTEND | Terms exist in `ydu_fitment_levels()`. Writes exist only in the seeder |
| Woo push | EXTEND | Seeder creates by SKU. No update client, no remote writer |
| Zoho API push | NEW | No HTTP client. Plans 2.7b is blocked on the same OAuth |
| Stock / base price ownership | REUSE | Spec §1 and §5.5. Trade plugin only filters display price |
| Google / Meta | REUSE | Live `google-listings-and-ads` and `facebook-for-woocommerce`. Not in this repo. Do not rebuild |
| CSV | REUSE | Live WebToffee importer. Studio still needs its own JSON |
| AI draft | NEW | No model client. Follow-up requires evidence link + downloaded picture per proposed number |
| eBay pull | NEW | No eBay client. Official Browse `getItemByLegacyId` plus Trading `GetItem` compatibility list |
| JPEG/WebP → PNG | EXTEND | PHP GD is already on the local WordPress PHP. No new image package. Zoho cap is 7 MB |
| Sync receipts | NEW | Seeder skips an existing SKU and stops |

Placement: a **separate local app** in this repo, run on localhost, pointed at local wp-env. Not `themes/ydu`. Not `plugins/ydu-fitment`. Not a plugin installed on test or production. Those zips ship to the shop; this app must not.

## Scoring

| Axis | Score /5 | Note |
|---|---|---|
| Product fit | 5 | This is the catalog workflow spec §1 non-goals deliberately left out of the rebuild |
| Evidence | 3 | Connector feed map and current product file are missing. Part-number pain is stated, not measured |
| User value | 5 | One editor instead of Woo and Zoho by hand |
| Feasibility | 3 | OAuth, feed conflict, and flat fitment are real |
| Regression safety | 2 | A live push can move stock or overwrite a product. Pull-only first |
| Leverage | 4 | Unblocks honest OEM search and cleaner Google MPNs later |

## Priority

**Required**

- Local studio, one screen, SQLite model above, import report, publish to local Woo only.
- eBay paste → photos, superseded numbers, and the car list when eBay returns it.
- AI numbers only with a stored link and a stored picture, then your tick.
- Hero click, PNG under 7 MB, rights tick before a photo leaves the PC.
- Title uses all 150 characters. Distinct numbers, superseded first, fill the title. Overflow goes in the first sentence of the description. Page 1 for the stocked number and each superseded number is the live acceptance check after indexing.
- Read-only export of the live Zoho feed map before any Zoho write.
- Receipts. No stock writes. No new taxonomy.

**Recommended**

- AI title and description drafts you accept field by field.
- Zoho sandbox upsert of name, SKU, rate, short description.
- Studio JSON export and Woo-shaped CSV.
- Channel readiness panel.

**Optional**

- Shop search that hits aliases (theme work, after this studio can export a confirmed alias list).
- Supersession graph picture.
- Composite kits.

**Reject**

- Zoho or wp-admin as the AI editor.
- Studio installed on ydu.com.au or test.ydu.com.au.
- Studio sending stock, opening stock, or trade last-price.
- Direct Google or Meta APIs in v1.
- Auto-publish.
- A second web page per part number.
- Treating `03L198119F` as covered because the title says `03L198119B`.
- Opening ETKA, Partslink24, or any logged-in catalog.
- Working around an eBay block page.
- Sending another seller's photo to Zoho or Woo without the rights tick.
- New vehicle taxonomy.
- Copying any database over production.
- Folding this into Plans 5.3. Theme launch still does not import a catalog.

## Spec delta (proposed, not applied)

Add a new spec section, **Catalog Studio**, and leave §1 non-goals in force for the theme rebuild:

- The studio is a local authoring master. It is not part of the theme or `ydu-fitment`.
- Production catalog writes remain forbidden except a later, explicit CEO publish gate.
- Zoho connector on the clone stays disabled.
- Fitment published by the studio uses existing `pa_*` terms only, and only for catalog paths still on the part.
- The studio vehicle catalog is reference data ordered year, make, model, submodel, variant, engine code. Shop dropdown behaviour is out of this workstream.
- Shelf price, stock, and trade price follow the table in this plan.
- Google and Meta remain the existing Woo plugins.
- One studio screen takes a pasted eBay item URL, holds AI number evidence (link and picture), converts the hero to PNG for Zoho, and writes a 150-character title that includes distinct alternate numbers, with any overflow in the first sentence of the description.
- Photos are pushed only after a rights tick. Dealer catalogs behind a login are out of scope. Google rank is not a success condition.

`Spec skip reason` does not apply. This changes external integrations and the write policy. It is not applied until you accept it.

## C0 method lock

Signed scope is C0 only. C1–C13 stay unsigned. This lock is the method.

- Verbs: GET only. No POST, PUT, PATCH, or DELETE. No feed Save, Sync, Test, Run, or manual send.
- Host: the live shop REST only (`ydu.com.au`). No call to Zoho, Google, Meta, eBay, or test.ydu.com.au. The clone connector stays disabled and is not opened.
- Products: a new `GET /wp-json/wc/v3/products`. Record the pull time and the request URL. Row count must equal `X-WP-Total` for the status set named in the note. Also record publish, draft, pending, and private counts. Each row stores id, sku, status, regular_price, sale_price, and stock_quantity. Do not copy `data/export/products-wc-v3.json`.
- Feeds: cover both stores named in the June system status, `vxc_zoho` and `wps_zoho_books_feed`. A GET that returns a feed is logged. If GET cannot read a feed, record the HTTP status and stop. Do not open wp-admin buttons that write.
- Redaction: the note and the product file must not contain an application password, access token, refresh token, client secret, or Zoho organisation auth. Account rows are omitted.
- Output: one note in `docs/` and one new product file. No theme code, no plugin code, no studio UI, no publish path.

## Phases

Theme phases 0–5 stay as they are. This workstream does not gate launch.

| Task | Description | DoD | Depends | Status |
|---|---|---|---|---|
| C0 | Read-only GET of products and of any feed-map endpoint that already answers GET. See **C0 method lock** | The note and the new product file exist. Every call in the HTTP log is GET. No Zoho call. No secret in either file. If a feed map is not available by GET, the note records the HTTP status and stops | — | blocked — live GET returned 401. See docs/c0-http-log.md. No product file kept |
| C1 | Local studio: items, aliases, fitment rows, import of that product file, clash report | A stocked item opens with its SKU unchanged and its numbers listed. Two items sharing a normalized number are flagged. No network write | C0 | proposed |
| C2 | Part screen at 1440×900: paste bar, photos, evidence, item, publish bar. Vehicle catalog is a separate page, not this screen | The five part regions are visible together. A click on a thumbnail sets the hero. Narrower widths stack on the same page | C1 | proposed |
| C8 | Paste an eBay item link. Walk every compatibility page. Match each page’s header to a stored template. An unknown header pauses for a mapping, which is saved to the database and to `data/table-templates.json`, then the walk resumes | Item `137092930759` stores 38 unique rows once its header template exists, including page 2. A second listing with that same header does not ask again. A page whose header has no template does not write shop fields until you save the mapping | C2 | proposed |
| C9 | AI proposes VW, Audi, Porsche, Skoda, Seat, Cupra, and superseded numbers on that same screen | Each row shows a link and a downloaded picture. A row missing either cannot be ticked. An unticked row cannot publish | C2 | proposed |
| C10 | Convert kept photos to PNG with PHP GD. Scale until under 7 MB | The hero you clicked is the PNG marked primary. The publish bar shows ready or the reason. No new image package | C8 | proposed |
| C11 | Embed every ticked distinct number as plain text in the product HTML and in the title or description the Google plugin sends | Stocking `03L198119B` with ticked `03L198119F`: the page source contains both exact strings, and the Shopping payload contains both. A number that appears only in a photo or a script fails the check | C9 | proposed |
| C12 | Vehicle catalog page. Seed it from the shop’s existing vehicles. Order the reference data year, make, model, submodel, variant, engine code. On the part screen, match each extracted row to that catalog | A row whose six fields already exist is linked and not highlighted. A missing path is highlighted, with Confirm and Delete. Confirm adds the path to the catalog. Delete removes it from the part. The shop finder dropdowns are not changed | C1, C8 | proposed |
| C13 | Side-by-side page. Pull the Zoho item and the WordPress product for one SKU and list every field | Left column is Zoho, right column is WordPress. A SKU in only one system shows an empty column. A field that differs is marked not aligned. The page writes nothing to either system | C0, C1 | proposed |
| C3 | Publish to local wp-env only: SEO title, description text, hero PNG, gallery PNGs, and fitment for catalog vehicles still on the part, compiled to existing `pa_*`. No stock, no sale price | Re-publish updates the same SKU. A highlighted vehicle with no Confirm is absent from the shop product. A deleted vehicle is absent. Local stock quantity is unchanged | C2, C10, C11, C12 | proposed |
| C4 | Zoho sandbox: upsert name, SKU, rate, short description. Upload the hero PNG as primary. Refuse if the payload contains a stock field or a non-PNG hero | Sandbox item matches SKU, rate, and primary image. Live Zoho org receives zero calls | C0, C3 | proposed |
| C5 | Readiness panel for the fields Google and Meta plugins already read | Each item shows pass/fail for image, price, brand, MPN or GTIN. No call to Google or Meta | C3 | proposed |
| C6 | JSON export and Woo-shaped CSV | Round-trip: export, re-import, same SKUs and aliases | C1 | proposed |
| C7 | Production pilot of one existing SKU | Blocked until you approve the feed-map change and the spec §2 exception. Receipt stored. Stock unchanged. Rollback is re-publish of the previous JSON | C4, C5, CEO | proposed |

## Production-push blockers

1. Spec §2 and Plans 5.3 forbid catalog edits on production and on the clone. C7 is a named exception, not a side effect of theme launch.
2. A Zoho API call from this PC hits the live organisation even when the clone connector is off. C4 uses a sandbox. C7 waits for you.
3. Compiling fitment into `pa_*` changes live `filter_*` results. There is no product JSON in the repo to diff against, and multi-make parts already leak. C3 proves the compile locally first.

## CEO decisions

1. Accept this as a **separate workstream**. Theme launch does not wait on it, and it does not write the shop until C7.
2. Accept the ownership table: studio authors, Zoho owns stock and orders, Woo owns the shop, Google/Meta stay on the current plugins.
3. Accept that the first live publish also requires you to **turn off whichever connector feed currently owns shelf price**, after C0 shows which feed that is.
4. Accept the screen rules: you paste an eBay item URL; a free eBay developer key is created once (not a subscription); AI numbers only with a link and a picture; PNG hero under 7 MB; a rights tick before a photo is sent. Page 1 for each ticked superseded number is checked on live Google after indexing. A miss moves that number into the first 70 characters and the check is repeated.

No shop spend. No new plugin on the shop. No new image package. Zoho OAuth for the sandbox is the same credential class already blocking Plans 2.7b. eBay keys are a separate free developer application.

## Common Promotion Candidates

None. This app is YDU-specific. Nothing here is a candidate for a shared UI package.

## Next action after approval

`/harness-work C0` — the method lock above. No other task.
