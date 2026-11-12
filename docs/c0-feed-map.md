# C0 feed map and product pull

Pulled: 2026-11-03 11:51:06 +08:00
Request URL: https://ydu.com.au/wp-json/wc/v3/products?status=any&per_page=100
Result: every GET returned 401. No product file was kept. The zeros below are not a catalog count.
X-WP-Total for status=any: not returned (401)
Rows written: 0
Status counts: not read (401)

Auth material is not in this note or the product file.

## Feeds

June system status named two stores: vxc_zoho (5) and wps_zoho_books_feed (4). This pull does not copy those rows.
GET https://ydu.com.au/wp-json/ returned no route whose name contains zoho, vxc_, or wps_zoho.
Feed field maps are not returned by a product GET. No Save, Sync, Test, or Run was sent. No Zoho host was called.
GET /wp-json/wp/v2/plugins did not return a body. See the HTTP log for the status. Feed map read stops here.
