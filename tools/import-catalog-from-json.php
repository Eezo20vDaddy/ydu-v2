<?php
/**
 * Import WooCommerce catalog from local JSON export (localhost only).
 *
 * docker exec ... wp eval-file wp-content/ydu-seed/tools/import-catalog-from-json.php --path=/var/www/html
 */

if ( ! defined( 'ABSPATH' ) ) {
	fwrite( STDERR, "Run via: wp eval-file wp-content/ydu-seed/tools/import-catalog-from-json.php\n" );
	exit( 1 );
}

$site = (string) get_option( 'siteurl' );
$host = (string) wp_parse_url( $site, PHP_URL_HOST );
if ( ! in_array( $host, array( 'localhost', '127.0.0.1' ), true ) ) {
	fwrite( STDERR, "Refusing non-local site: {$host}\n" );
	exit( 1 );
}

set_time_limit( 0 );
if ( function_exists( 'wp_raise_memory_limit' ) ) {
	wp_raise_memory_limit( 'admin' );
}

require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/media.php';
require_once ABSPATH . 'wp-admin/includes/image.php';

$export_dir = WP_CONTENT_DIR . '/ydu-seed/data/export';
$cats_path  = $export_dir . '/product-categories.json';
$prod_path  = $export_dir . '/products-wc-v3.json';

if ( ! is_readable( $cats_path ) || ! is_readable( $prod_path ) ) {
	fwrite( STDERR, "Missing export JSON under {$export_dir}\n" );
	exit( 1 );
}

$cats_raw = json_decode( (string) file_get_contents( $cats_path ), true );
$prods_raw = json_decode( (string) file_get_contents( $prod_path ), true );
if ( ! is_array( $cats_raw ) || ! is_array( $prods_raw ) ) {
	fwrite( STDERR, "Invalid JSON in export files\n" );
	exit( 1 );
}

$report = ydu_catalog_import_run( $cats_raw, $prods_raw );
echo wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . "\n";

/**
 * @param array<int, array<string, mixed>> $categories
 * @param array<int, array<string, mixed>> $products
 * @return array<string, mixed>
 */
function ydu_catalog_import_run( array $categories, array $products ): array {
	$cat_slug_map = ydu_import_product_categories( $categories );
	ydu_collect_and_register_attributes( $products );

	$stats = array(
		'source_rows'        => count( $products ),
		'imported'           => 0,
		'updated'            => 0,
		'created'            => 0,
		'skipped'            => 0,
		'publish'            => 0,
		'draft'              => 0,
		'other_status'       => 0,
		'featured_local'     => 0,
		'featured_expected'  => 0,
		'failures'           => array(),
		'sample_product_url' => '',
	);

	$first_publish_slug = '';
	foreach ( $products as $row ) {
		if ( ! is_array( $row ) ) {
			++$stats['skipped'];
			$stats['failures'][] = array( 'sku' => '', 'reason' => 'invalid row' );
			continue;
		}

		$result = ydu_import_one_product( $row, $cat_slug_map );
		if ( empty( $result['ok'] ) ) {
			++$stats['skipped'];
			$stats['failures'][] = array(
				'sku'    => (string) ( $row['sku'] ?? '' ),
				'slug'   => (string) ( $row['slug'] ?? '' ),
				'reason' => (string) ( $result['error'] ?? 'unknown' ),
			);
			continue;
		}

		++$stats['imported'];
		if ( ! empty( $result['created'] ) ) {
			++$stats['created'];
		} else {
			++$stats['updated'];
		}

		$status = (string) ( $row['status'] ?? 'publish' );
		if ( $status === 'publish' ) {
			++$stats['publish'];
			if ( $first_publish_slug === '' && ! empty( $row['slug'] ) ) {
				$first_publish_slug = (string) $row['slug'];
			}
		} elseif ( $status === 'draft' ) {
			++$stats['draft'];
		} else {
			++$stats['other_status'];
		}

		if ( ! empty( $result['had_source_image'] ) ) {
			++$stats['featured_expected'];
			if ( ! empty( $result['featured_local'] ) ) {
				++$stats['featured_local'];
			}
		}
	}

	if ( $first_publish_slug !== '' ) {
		$stats['sample_product_url'] = home_url( '/product/' . $first_publish_slug . '/' );
	}

	return $stats;
}

/**
 * @param array<int, array<string, mixed>> $categories
 * @return array<string, int> slug => term_id
 */
function ydu_import_product_categories( array $categories ): array {
	$slug_map = array();
	usort(
		$categories,
		static function ( $a, $b ) {
			return (int) ( $a['parent'] ?? 0 ) <=> (int) ( $b['parent'] ?? 0 );
		}
	);

	foreach ( $categories as $cat ) {
		if ( ! is_array( $cat ) ) {
			continue;
		}
		$slug = sanitize_title( (string) ( $cat['slug'] ?? '' ) );
		$name = (string) ( $cat['name'] ?? $slug );
		if ( $slug === '' ) {
			continue;
		}

		$existing = get_term_by( 'slug', $slug, 'product_cat' );
		if ( $existing && ! is_wp_error( $existing ) ) {
			$slug_map[ $slug ] = (int) $existing->term_id;
			continue;
		}

		$parent_slug = 0;
		$parent_id   = (int) ( $cat['parent'] ?? 0 );
		if ( $parent_id > 0 ) {
			foreach ( $categories as $maybe_parent ) {
				if ( is_array( $maybe_parent ) && (int) ( $maybe_parent['id'] ?? 0 ) === $parent_id ) {
					$p_slug = sanitize_title( (string) ( $maybe_parent['slug'] ?? '' ) );
					if ( $p_slug !== '' && isset( $slug_map[ $p_slug ] ) ) {
						$parent_slug = $slug_map[ $p_slug ];
					}
					break;
				}
			}
		}

		$inserted = wp_insert_term(
			$name,
			'product_cat',
			array(
				'slug'        => $slug,
				'description' => (string) ( $cat['description'] ?? '' ),
				'parent'      => (int) $parent_slug,
			)
		);
		if ( is_wp_error( $inserted ) ) {
			$again = get_term_by( 'slug', $slug, 'product_cat' );
			if ( $again && ! is_wp_error( $again ) ) {
				$slug_map[ $slug ] = (int) $again->term_id;
			}
			continue;
		}
		$slug_map[ $slug ] = (int) $inserted['term_id'];
	}

	return $slug_map;
}

/**
 * @param array<int, array<string, mixed>> $products
 */
function ydu_collect_and_register_attributes( array $products ): void {
	$needed = array();
	foreach ( $products as $row ) {
		if ( ! is_array( $row ) || empty( $row['attributes'] ) || ! is_array( $row['attributes'] ) ) {
			continue;
		}
		foreach ( $row['attributes'] as $attr ) {
			if ( ! is_array( $attr ) ) {
				continue;
			}
			$tax = (string) ( $attr['slug'] ?? '' );
			if ( $tax === '' || ! str_starts_with( $tax, 'pa_' ) ) {
				continue;
			}
			$needed[ $tax ] = (string) ( $attr['name'] ?? $tax );
		}
	}

	foreach ( $needed as $taxonomy => $label ) {
		ydu_ensure_global_attribute( $taxonomy, $label );
	}
	ydu_reregister_product_attribute_taxonomies();
}

function ydu_ensure_global_attribute( string $taxonomy, string $label ): void {
	if ( taxonomy_exists( $taxonomy ) ) {
		return;
	}
	$attr_name = str_replace( 'pa_', '', $taxonomy );
	if ( wc_attribute_taxonomy_id_by_name( $attr_name ) ) {
		return;
	}
	$result = wc_create_attribute(
		array(
			'name'         => $label !== '' ? $label : $attr_name,
			'slug'         => $attr_name,
			'type'         => 'select',
			'order_by'     => 'menu_order',
			'has_archives' => false,
		)
	);
	if ( is_wp_error( $result ) ) {
		return;
	}
	delete_transient( 'wc_attribute_taxonomies' );
}

function ydu_reregister_product_attribute_taxonomies(): void {
	delete_transient( 'wc_attribute_taxonomies' );
	$attributes = wc_get_attribute_taxonomies();
	if ( ! is_array( $attributes ) ) {
		return;
	}
	foreach ( $attributes as $attribute ) {
		$name = wc_attribute_taxonomy_name( $attribute->attribute_name );
		if ( taxonomy_exists( $name ) ) {
			continue;
		}
		register_taxonomy(
			$name,
			apply_filters( 'woocommerce_taxonomy_objects_' . $name, array( 'product' ) ),
			apply_filters(
				'woocommerce_taxonomy_args_' . $name,
				array(
					'hierarchical' => false,
					'show_ui'      => false,
					'query_var'    => true,
					'rewrite'      => false,
					'public'       => false,
				)
			)
		);
	}
}

/**
 * @param array<string, mixed> $row
 * @param array<string, int>   $cat_slug_map
 * @return array<string, mixed>
 */
function ydu_import_one_product( array $row, array $cat_slug_map ): array {
	$sku  = (string) ( $row['sku'] ?? '' );
	$slug = sanitize_title( (string) ( $row['slug'] ?? '' ) );
	$type = (string) ( $row['type'] ?? 'simple' );
	if ( $type !== 'simple' ) {
		return array( 'ok' => false, 'error' => 'unsupported type ' . $type );
	}

	$product_id = ydu_find_product_id( $sku, $slug );
	$created    = false;
	if ( $product_id > 0 ) {
		$product = wc_get_product( $product_id );
		if ( ! $product || ! $product->is_type( 'simple' ) ) {
			return array( 'ok' => false, 'error' => 'existing product is not simple' );
		}
	} else {
		$product = new WC_Product_Simple();
		$created = true;
	}

	$name = (string) ( $row['name'] ?? $sku );
	if ( $name === '' ) {
		return array( 'ok' => false, 'error' => 'missing name' );
	}

	$product->set_name( $name );
	if ( $slug !== '' ) {
		$product->set_slug( $slug );
	}
	if ( $sku !== '' ) {
		$product->set_sku( $sku );
	}

	$status = (string) ( $row['status'] ?? 'publish' );
	if ( in_array( $status, array( 'publish', 'draft', 'pending', 'private' ), true ) ) {
		$product->set_status( $status );
	}

	$visibility = (string) ( $row['catalog_visibility'] ?? 'visible' );
	$map        = array(
		'visible' => 'visible',
		'catalog' => 'catalog',
		'search'  => 'search',
		'hidden'  => 'hidden',
	);
	$product->set_catalog_visibility( $map[ $visibility ] ?? 'visible' );

	$product->set_description( (string) ( $row['description'] ?? '' ) );
	$product->set_short_description( (string) ( $row['short_description'] ?? '' ) );
	$product->set_regular_price( (string) ( $row['regular_price'] ?? '' ) );
	$sale = (string) ( $row['sale_price'] ?? '' );
	$product->set_sale_price( $sale !== '' ? $sale : '' );

	$manage = ! empty( $row['manage_stock'] );
	$product->set_manage_stock( $manage );
	if ( $manage && array_key_exists( 'stock_quantity', $row ) && $row['stock_quantity'] !== null && $row['stock_quantity'] !== '' ) {
		$product->set_stock_quantity( (int) $row['stock_quantity'] );
	}
	$stock_status = (string) ( $row['stock_status'] ?? 'instock' );
	if ( in_array( $stock_status, array( 'instock', 'outofstock', 'onbackorder' ), true ) ) {
		$product->set_stock_status( $stock_status );
	}

	$product->set_reviews_allowed( ! empty( $row['reviews_allowed'] ) );
	$product->set_featured( ! empty( $row['featured'] ) );

	$cat_ids = array();
	if ( ! empty( $row['categories'] ) && is_array( $row['categories'] ) ) {
		foreach ( $row['categories'] as $cat ) {
			if ( ! is_array( $cat ) ) {
				continue;
			}
			$cslug = sanitize_title( (string) ( $cat['slug'] ?? '' ) );
			if ( $cslug !== '' && isset( $cat_slug_map[ $cslug ] ) ) {
				$cat_ids[] = (int) $cat_slug_map[ $cslug ];
			}
		}
	}
	$product->set_category_ids( array_values( array_unique( $cat_ids ) ) );

	$tag_ids = array();
	if ( ! empty( $row['tags'] ) && is_array( $row['tags'] ) ) {
		foreach ( $row['tags'] as $tag ) {
			if ( ! is_array( $tag ) ) {
				continue;
			}
			$tname = (string) ( $tag['name'] ?? '' );
			if ( $tname === '' ) {
				continue;
			}
			$term = term_exists( $tname, 'product_tag' );
			if ( ! $term ) {
				$term = wp_insert_term( $tname, 'product_tag' );
			}
			if ( is_wp_error( $term ) ) {
				continue;
			}
			$tag_ids[] = (int) ( is_array( $term ) ? $term['term_id'] : $term );
		}
	}
	if ( $tag_ids ) {
		wp_set_object_terms( $product->get_id(), $tag_ids, 'product_tag' );
	}

	$product_id = $product->save();
	if ( ! $product_id ) {
		return array( 'ok' => false, 'error' => 'product save failed' );
	}

	ydu_apply_product_attributes( $product_id, $row );

	$images        = is_array( $row['images'] ?? null ) ? $row['images'] : array();
	$had_source    = count( $images ) > 0;
	$featured_local = false;
	$gallery_ids    = array();

	if ( $had_source ) {
		foreach ( $images as $index => $img ) {
			if ( ! is_array( $img ) ) {
				continue;
			}
			$url = (string) ( $img['src'] ?? '' );
			if ( $url === '' ) {
				continue;
			}
			$aid = ydu_sideload_product_image( $url, $product_id, (string) ( $img['alt'] ?? '' ) );
			if ( $aid <= 0 ) {
				continue;
			}
			if ( $index === 0 ) {
				set_post_thumbnail( $product_id, $aid );
				$featured_local = true;
			} else {
				$gallery_ids[] = $aid;
			}
		}
		if ( $gallery_ids ) {
			$product = wc_get_product( $product_id );
			if ( $product ) {
				$product->set_gallery_image_ids( $gallery_ids );
				$product->save();
			}
		}
	}

	return array(
		'ok'               => true,
		'created'          => $created,
		'product_id'       => $product_id,
		'had_source_image' => $had_source,
		'featured_local'   => $featured_local,
	);
}

/**
 * @param array<string, mixed> $row
 */
function ydu_apply_product_attributes( int $product_id, array $row ): void {
	if ( empty( $row['attributes'] ) || ! is_array( $row['attributes'] ) ) {
		return;
	}

	$wc_attrs = array();
	foreach ( $row['attributes'] as $attr ) {
		if ( ! is_array( $attr ) ) {
			continue;
		}
		$taxonomy = (string) ( $attr['slug'] ?? '' );
		if ( $taxonomy === '' || ! str_starts_with( $taxonomy, 'pa_' ) ) {
			continue;
		}
		if ( ! taxonomy_exists( $taxonomy ) ) {
			ydu_ensure_global_attribute( $taxonomy, (string) ( $attr['name'] ?? $taxonomy ) );
			ydu_reregister_product_attribute_taxonomies();
		}

		$options = is_array( $attr['options'] ?? null ) ? $attr['options'] : array();
		$term_ids = array();
		foreach ( $options as $option ) {
			$option = (string) $option;
			if ( $option === '' ) {
				continue;
			}
			$term = term_exists( $option, $taxonomy );
			if ( ! $term ) {
				$term = wp_insert_term( $option, $taxonomy );
			}
			if ( is_wp_error( $term ) ) {
				continue;
			}
			$term_ids[] = (int) ( is_array( $term ) ? $term['term_id'] : $term );
		}
		if ( $term_ids ) {
			wp_set_object_terms( $product_id, $term_ids, $taxonomy );
		}

		$attr_name = str_replace( 'pa_', '', $taxonomy );
		$attr_id   = wc_attribute_taxonomy_id_by_name( $attr_name );
		$wc_attr   = new WC_Product_Attribute();
		if ( $attr_id ) {
			$wc_attr->set_id( (int) $attr_id );
		}
		$wc_attr->set_name( $taxonomy );
		$wc_attr->set_options( $term_ids );
		$wc_attr->set_visible( ! empty( $attr['visible'] ) );
		$wc_attr->set_variation( ! empty( $attr['variation'] ) );
		$wc_attrs[] = $wc_attr;
	}

	if ( $wc_attrs ) {
		$product = wc_get_product( $product_id );
		if ( $product ) {
			$product->set_attributes( $wc_attrs );
			$product->save();
		}
	}
}

function ydu_find_product_id( string $sku, string $slug ): int {
	if ( $sku !== '' ) {
		$id = wc_get_product_id_by_sku( $sku );
		if ( $id ) {
			return (int) $id;
		}
	}
	if ( $slug !== '' ) {
		$posts = get_posts(
			array(
				'name'           => $slug,
				'post_type'      => 'product',
				'post_status'    => 'any',
				'posts_per_page' => 1,
				'fields'         => 'ids',
			)
		);
		if ( $posts ) {
			return (int) $posts[0];
		}
	}
	return 0;
}

/** @var array<string, int> */
$GLOBALS['ydu_image_url_cache'] = array();

function ydu_sideload_product_image( string $url, int $product_id, string $alt = '' ): int {
	if ( isset( $GLOBALS['ydu_image_url_cache'][ $url ] ) ) {
		return (int) $GLOBALS['ydu_image_url_cache'][ $url ];
	}

	$host = (string) wp_parse_url( $url, PHP_URL_HOST );
	if ( $host !== 'ydu.com.au' && $host !== 'www.ydu.com.au' ) {
		return 0;
	}

	add_filter( 'http_request_timeout', 'ydu_import_http_timeout' );
	$tmp = download_url( $url );
	remove_filter( 'http_request_timeout', 'ydu_import_http_timeout' );

	if ( is_wp_error( $tmp ) ) {
		return 0;
	}

	$name = wp_basename( wp_parse_url( $url, PHP_URL_PATH ) ?? 'image.jpg' );
	$file = array(
		'name'     => $name,
		'tmp_name' => $tmp,
		'error'    => 0,
		'size'     => (int) @filesize( $tmp ),
	);

	$aid = media_handle_sideload( $file, $product_id );
	if ( is_wp_error( $aid ) ) {
		@unlink( $tmp );
		return 0;
	}

	if ( $alt !== '' ) {
		update_post_meta( (int) $aid, '_wp_attachment_image_alt', sanitize_text_field( $alt ) );
	}
	update_post_meta( (int) $aid, '_ydu_source_url', esc_url_raw( $url ) );

	$GLOBALS['ydu_image_url_cache'][ $url ] = (int) $aid;
	return (int) $aid;
}

function ydu_import_http_timeout(): int {
	return 45;
}
