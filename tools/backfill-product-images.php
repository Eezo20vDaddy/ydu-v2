<?php
/**
 * Backfill featured images for seeded products that don't have one yet,
 * sideloading from the production URLs in data/products-store-api.json.
 * Matched by SKU. Idempotent — products with a thumbnail are skipped.
 *
 * Usage: wp eval-file wp-content/ydu-seed/tools/backfill-product-images.php
 */

defined( 'WP_CLI' ) && WP_CLI || exit( "wp-cli only\n" );

$seed_dir      = WP_CONTENT_DIR . '/ydu-seed/data';
$products_json = json_decode( file_get_contents( $seed_dir . '/products-store-api.json' ), true );

if ( ! $products_json ) {
	WP_CLI::error( 'Could not read seed JSON.' );
}

require_once ABSPATH . 'wp-admin/includes/media.php';
require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/image.php';

$done    = 0;
$skipped = 0;
$no_url  = 0;
$failed  = 0;

foreach ( $products_json as $p ) {
	$sku = (string) ( $p['sku'] ?? '' );
	if ( '' === $sku ) {
		continue;
	}
	$product_id = wc_get_product_id_by_sku( $sku );
	if ( ! $product_id ) {
		continue;
	}
	if ( has_post_thumbnail( $product_id ) ) {
		$skipped++;
		continue;
	}
	if ( empty( $p['images'][0] ) ) {
		$no_url++;
		continue;
	}
	$attachment_id = media_sideload_image( $p['images'][0], $product_id, null, 'id' );
	if ( is_wp_error( $attachment_id ) ) {
		$failed++;
		WP_CLI::log( "  FAIL {$sku}: " . $attachment_id->get_error_message() );
		continue;
	}
	set_post_thumbnail( $product_id, $attachment_id );
	$done++;
	if ( 0 === $done % 25 ) {
		WP_CLI::log( "  …{$done} images" );
	}
}

WP_CLI::success( "Images added: {$done}, already had: {$skipped}, no source URL on live site: {$no_url}, failed: {$failed}" );
