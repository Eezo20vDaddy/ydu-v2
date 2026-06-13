<?php
/**
 * Seed the local wp-env WooCommerce store with the real YDU catalog exported
 * from production (data/products-store-api.json + data/attribute-terms.json).
 *
 * Local/dev use only — never runs against a remote site. Idempotent: existing
 * attributes, terms, and SKUs are skipped, so re-running is safe.
 *
 * Usage: wp eval-file wp-content/ydu-seed/tools/seed-local-products.php [max_images]
 */

defined( 'WP_CLI' ) && WP_CLI || exit( "wp-cli only\n" );

if ( ! class_exists( 'WooCommerce' ) ) {
	WP_CLI::error( 'WooCommerce is not active.' );
}

$seed_dir   = WP_CONTENT_DIR . '/ydu-seed/data';
$max_images = isset( $args[0] ) ? absint( $args[0] ) : 40;

$terms_json    = json_decode( file_get_contents( $seed_dir . '/attribute-terms.json' ), true );
$products_json = json_decode( file_get_contents( $seed_dir . '/products-store-api.json' ), true );

if ( ! $terms_json || ! $products_json ) {
	WP_CLI::error( 'Could not read seed JSON from ' . $seed_dir );
}

// Map export keys -> Woo attribute slugs (taxonomy = pa_<slug>, matching production).
$attribute_slugs = array(
	'year'         => 'year_alt',
	'make'         => 'make',
	'model'        => 'model',
	'submodel'     => 'submodel',
	'variant'      => 'variant',
	'engine_code'  => 'engine_code',
	'engine_type'  => 'engine_type',
	'transmission' => 'transmission',
);

foreach ( $attribute_slugs as $key => $slug ) {
	if ( ! taxonomy_exists( 'pa_' . $slug ) ) {
		$result = wc_create_attribute( array(
			'name' => ucwords( str_replace( '_', ' ', $key ) ),
			'slug' => $slug,
			'type' => 'select',
		) );
		if ( is_wp_error( $result ) ) {
			WP_CLI::error( "Attribute {$slug}: " . $result->get_error_message() );
		}
	}
}

// Taxonomies registered by wc_create_attribute become available after re-registration.
unset( $GLOBALS['wc_product_attributes'] );
delete_transient( 'wc_attribute_taxonomies' );
WC_Cache_Helper::invalidate_cache_group( 'woocommerce-attributes' );
$attr_count = 0;

foreach ( $attribute_slugs as $key => $slug ) {
	$taxonomy = 'pa_' . $slug;
	if ( ! taxonomy_exists( $taxonomy ) ) {
		register_taxonomy( $taxonomy, 'product', array( 'hierarchical' => false, 'public' => false ) );
	}
	foreach ( $terms_json[ $key ] ?? array() as $term ) {
		if ( ! term_exists( $term['slug'], $taxonomy ) ) {
			$created = wp_insert_term( $term['name'], $taxonomy, array( 'slug' => $term['slug'] ) );
			if ( ! is_wp_error( $created ) ) {
				$attr_count++;
			}
		}
	}
}
WP_CLI::log( "Attribute terms created: {$attr_count}" );

$created = 0;
$skipped = 0;
$images  = 0;

foreach ( $products_json as $p ) {
	$sku = (string) ( $p['sku'] ?? '' );
	if ( '' !== $sku && wc_get_product_id_by_sku( $sku ) ) {
		$skipped++;
		continue;
	}

	$product = new WC_Product_Simple();
	$product->set_name( html_entity_decode( $p['name'], ENT_QUOTES | ENT_HTML5 ) );
	if ( '' !== $sku ) {
		$product->set_sku( $sku );
	}

	// Store API prices are in minor units (cents).
	$regular = ( $p['regular_price'] ?? $p['price'] ?? 0 ) / 100;
	$product->set_regular_price( (string) $regular );
	if ( ! empty( $p['on_sale'] ) && isset( $p['sale_price'] ) ) {
		$product->set_sale_price( (string) ( $p['sale_price'] / 100 ) );
	}
	$product->set_stock_status( $p['stock_status'] ?? 'instock' );

	$cat_ids = array();
	foreach ( $p['categories'] ?? array() as $cat ) {
		$existing = term_exists( $cat['slug'], 'product_cat' );
		if ( ! $existing ) {
			$existing = wp_insert_term( $cat['name'], 'product_cat', array( 'slug' => $cat['slug'] ) );
		}
		if ( ! is_wp_error( $existing ) ) {
			$cat_ids[] = (int) ( is_array( $existing ) ? $existing['term_id'] : $existing );
		}
	}
	$product->set_category_ids( $cat_ids );

	$wc_attributes = array();
	$position      = 0;
	foreach ( $p['attributes'] ?? array() as $attr ) {
		$taxonomy = $attr['taxonomy'];
		if ( ! taxonomy_exists( $taxonomy ) ) {
			continue;
		}
		$term_ids = array();
		foreach ( $attr['terms'] as $t ) {
			$found = get_term_by( 'slug', $t['slug'], $taxonomy );
			if ( $found ) {
				$term_ids[] = (int) $found->term_id;
			}
		}
		if ( ! $term_ids ) {
			continue;
		}
		$wc_attr = new WC_Product_Attribute();
		$wc_attr->set_id( wc_attribute_taxonomy_id_by_name( $taxonomy ) );
		$wc_attr->set_name( $taxonomy );
		$wc_attr->set_options( $term_ids );
		$wc_attr->set_position( $position++ );
		$wc_attr->set_visible( true );
		$wc_attributes[] = $wc_attr;
	}
	$product->set_attributes( $wc_attributes );

	$product_id = $product->save();

	// Assign attribute terms directly as well — set_attributes() stores the
	// definition, but the term relationships drive filtering.
	foreach ( $wc_attributes as $wc_attr ) {
		wp_set_object_terms( $product_id, $wc_attr->get_options(), $wc_attr->get_name() );
	}

	if ( $images < $max_images && ! empty( $p['images'][0] ) ) {
		require_once ABSPATH . 'wp-admin/includes/media.php';
		require_once ABSPATH . 'wp-admin/includes/file.php';
		require_once ABSPATH . 'wp-admin/includes/image.php';
		$attachment_id = media_sideload_image( $p['images'][0], $product_id, null, 'id' );
		if ( ! is_wp_error( $attachment_id ) ) {
			set_post_thumbnail( $product_id, $attachment_id );
			$images++;
		}
	}

	$created++;
	if ( 0 === $created % 50 ) {
		WP_CLI::log( "  …{$created} products" );
	}
}

WP_CLI::success( "Products created: {$created}, skipped (existing SKU): {$skipped}, images sideloaded: {$images}" );
