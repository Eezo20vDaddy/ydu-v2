<?php
/**
 * Local shop only. Read or upsert a product by SKU.
 * Refuses any site whose URL is not localhost.
 *
 * wp eval-file studio-woo.php
 * Request JSON: wp-content/ydu-seed/data/studio-jobs/request.json
 * Response JSON: wp-content/ydu-seed/data/studio-jobs/response.json
 */

if ( ! defined( 'ABSPATH' ) ) {
	fwrite( STDERR, "run via wp eval-file\n" );
	exit( 1 );
}

if ( ! defined( 'STUDIO_WOO_EMBED' ) ) {
	studio_woo_run();
}

/**
 * @return array{ok:false,error:string}|null
 */
function studio_nonlocal_error(): ?array {
	$site = (string) get_option( 'siteurl' );
	$host = (string) wp_parse_url( $site, PHP_URL_HOST );
	if ( ! in_array( $host, array( 'localhost', '127.0.0.1' ), true ) ) {
		return array( 'ok' => false, 'error' => 'refusing non-local site ' . $host );
	}
	return null;
}

/**
 * Local shop request runner. Define STUDIO_WOO_EMBED before including this file
 * to load the functions without reading a request.
 */
function studio_woo_run(): void {
	$blocked = studio_nonlocal_error();
	if ( $blocked ) {
		studio_out( $blocked );
	}

	$req_path = WP_CONTENT_DIR . '/ydu-seed/data/studio-jobs/request.json';
	$req      = json_decode( (string) file_get_contents( $req_path ), true );
	if ( ! is_array( $req ) ) {
		studio_out( array( 'ok' => false, 'error' => 'bad request' ) );
	}

	$action = (string) ( $req['action'] ?? '' );
	if ( $action === 'skus' ) {
		$ids  = wc_get_products(
			array(
				'limit'  => -1,
				'return' => 'ids',
				'status' => array( 'publish', 'draft', 'pending', 'private' ),
			)
		);
		$skus = array();
		foreach ( $ids as $id ) {
			$sku = (string) get_post_meta( $id, '_sku', true );
			if ( $sku !== '' ) {
				$skus[] = $sku;
			}
		}
		studio_out( array( 'ok' => true, 'skus' => $skus ) );
	}
	if ( $action === 'one' ) {
		$id = wc_get_product_id_by_sku( (string) ( $req['sku'] ?? '' ) );
		$p  = $id ? wc_get_product( $id ) : null;
		studio_out( array( 'ok' => true, 'product' => $p ? studio_pack_product( $p ) : null ) );
	}
	if ( $action === 'list' ) {
		studio_out( array( 'ok' => true, 'products' => studio_list_products() ) );
	}
	if ( $action === 'upsert' ) {
		studio_out( studio_upsert( $req ) );
	}
	studio_out( array( 'ok' => false, 'error' => 'unknown action' ) );
}

function studio_out( array $data ): void {
	$path = WP_CONTENT_DIR . '/ydu-seed/data/studio-jobs/response.json';
	file_put_contents( $path, wp_json_encode( $data ) );
	echo wp_json_encode( array( 'ok' => ! empty( $data['ok'] ) ) );
	exit( 0 );
}

function studio_pack_product( WC_Product $p ): array {
	$meta = array();
	foreach ( $p->get_meta_data() as $row ) {
		$data = $row->get_data();
		$meta[ (string) $data['key'] ] = $data['value'];
	}
	$attrs = array();
	foreach ( $p->get_attributes() as $attr ) {
		$attrs[ $attr->get_name() ] = $attr->get_options();
	}
	$images = array();
	if ( $p->get_image_id() ) {
		$images[] = (string) wp_get_attachment_url( $p->get_image_id() );
	}
	foreach ( $p->get_gallery_image_ids() as $gid ) {
		$images[] = (string) wp_get_attachment_url( $gid );
	}
	return array(
		'id'                => $p->get_id(),
		'sku'               => (string) $p->get_sku(),
		'name'              => $p->get_name(),
		'status'            => $p->get_status(),
		'regular_price'     => $p->get_regular_price(),
		'sale_price'        => $p->get_sale_price(),
		'stock_quantity'    => $p->get_stock_quantity(),
		'description'       => $p->get_description(),
		'short_description' => $p->get_short_description(),
		'attributes'        => $attrs,
		'images'            => $images,
		'meta'              => $meta,
	);
}

function studio_list_products(): array {
	$ids = wc_get_products(
		array(
			'limit'  => -1,
			'return' => 'ids',
			'status' => array( 'publish', 'draft', 'pending', 'private' ),
		)
	);
	$out = array();
	foreach ( $ids as $id ) {
		$p = wc_get_product( $id );
		if ( $p ) {
			$out[] = studio_pack_product( $p );
		}
	}
	return $out;
}

function studio_upsert( array $req ): array {
	$blocked = studio_nonlocal_error();
	if ( $blocked ) {
		return $blocked;
	}
	$sku = (string) ( $req['sku'] ?? '' );
	if ( $sku === '' ) {
		return array( 'ok' => false, 'error' => 'missing sku' );
	}
	if ( array_key_exists( 'stock_quantity', $req ) || array_key_exists( 'sale_price', $req ) ) {
		return array( 'ok' => false, 'error' => 'stock and sale price are not accepted' );
	}
	$id = wc_get_product_id_by_sku( $sku );
	$p  = $id ? wc_get_product( $id ) : new WC_Product_Simple();
	if ( ! $p ) {
		$p = new WC_Product_Simple();
	}
	$before_stock = $p->get_id() ? $p->get_stock_quantity() : null;
	$p->set_sku( $sku );
	$p->set_name( (string) ( $req['name'] ?? $sku ) );
	$p->set_regular_price( (string) ( $req['regular_price'] ?? '' ) );
	$p->set_description( (string) ( $req['description'] ?? '' ) );
	$p->set_short_description( (string) ( $req['short_description'] ?? '' ) );
	$p->set_status( 'publish' );
	if ( $before_stock !== null ) {
		$p->set_stock_quantity( $before_stock );
	}
	$pid = (int) $p->save();

	$hero = (string) ( $req['hero_path'] ?? '' );
	if ( $hero !== '' && is_file( $hero ) ) {
		$allowed = realpath( WP_CONTENT_DIR . '/ydu-seed/data/studio-media' );
		$real    = realpath( $hero );
		if ( $allowed && $real && str_starts_with( $real, $allowed ) ) {
			require_once ABSPATH . 'wp-admin/includes/file.php';
			require_once ABSPATH . 'wp-admin/includes/media.php';
			require_once ABSPATH . 'wp-admin/includes/image.php';
			$tmp = wp_tempnam( basename( $real ) );
			copy( $real, $tmp );
			$file = array(
				'name'     => basename( $real ),
				'tmp_name' => $tmp,
				'error'    => 0,
				'size'     => filesize( $real ),
			);
			$aid = media_handle_sideload( $file, $pid );
			if ( ! is_wp_error( $aid ) ) {
				set_post_thumbnail( $pid, $aid );
			}
		}
	}

	$missing = array();
	if ( array_key_exists( 'upsell_skus', $req ) || array_key_exists( 'crosssell_skus', $req ) ) {
		$p          = wc_get_product( $pid );
		$upsell_ids = studio_ids_for_skus( (array) ( $req['upsell_skus'] ?? array() ), $missing );
		$cross_ids  = studio_ids_for_skus( (array) ( $req['crosssell_skus'] ?? array() ), $missing );
		$p->set_upsell_ids( $upsell_ids );
		$p->set_cross_sell_ids( $cross_ids );
		$p->save();
		studio_mirror_links( (int) $pid, $upsell_ids, 'upsell' );
		studio_mirror_links( (int) $pid, $cross_ids, 'cross' );
	}

	$fitment  = is_array( $req['fitment'] ?? null ) ? $req['fitment'] : array();
	$vehicles = studio_merge_vehicle_terms( $pid, $fitment );
	if ( $fitment !== array() ) {
		studio_store_fitment_applications( $pid, $fitment );
	}

	$saved = wc_get_product( $pid );
	return array(
		'ok'               => true,
		'woo_product_id'   => $pid,
		'stock_quantity'   => $saved ? $saved->get_stock_quantity() : null,
		'unresolved_links' => $missing,
		'vehicles'         => $vehicles,
	);
}

/**
 * Flat WooCommerce attribute taxonomies that store the part-to-vehicle mapping.
 *
 * @return array<string,string>
 */
function studio_vehicle_levels(): array {
	return array(
		'year'        => 'pa_year_alt',
		'make'        => 'pa_make',
		'model'       => 'pa_model',
		'submodel'    => 'pa_submodel',
		'variant'     => 'pa_variant',
		'engine_code' => 'pa_engine_code',
	);
}

/**
 * Add confirmed fitment names onto the vehicle terms already on the product.
 * Names are unioned per taxonomy. An empty incoming list does not call
 * wp_set_object_terms, so existing cars stay. Nothing is removed.
 *
 * @param array<int,mixed> $fitment
 * @return array{kept_count:int,added_count:int,added:string[],counts:array<string,int>,kept:array<string,string[]>,names:array<string,string[]>}
 */
function studio_merge_vehicle_terms( int $product_id, array $fitment ): array {
	$report = array(
		'kept_count'  => 0,
		'added_count' => 0,
		'added'       => array(),
		'counts'      => array(),
		'kept'        => array(),
		'names'       => array(),
	);
	if ( $product_id <= 0 ) {
		foreach ( studio_vehicle_levels() as $level => $taxonomy ) {
			$report['kept'][ $level ]   = array();
			$report['names'][ $level ]  = array();
			$report['counts'][ $level ] = 0;
		}
		return $report;
	}

	foreach ( studio_vehicle_levels() as $level => $taxonomy ) {
		$current = studio_object_terms( $product_id, $taxonomy );
		if ( is_wp_error( $current ) ) {
			$report['kept'][ $level ]   = array();
			$report['names'][ $level ]  = array();
			$report['counts'][ $level ] = 0;
			continue;
		}

		$current_ids   = array();
		$current_names = array();
		foreach ( $current as $term ) {
			$term_id = (int) $term->term_id;
			if ( $term_id <= 0 ) {
				continue;
			}
			$current_ids[]   = $term_id;
			$current_names[] = (string) $term->name;
		}

		$incoming = studio_incoming_names( $fitment, $level );
		$new_ids  = array();
		if ( $incoming !== array() && taxonomy_exists( $taxonomy ) ) {
			foreach ( $incoming as $name ) {
				$term_id = studio_ensure_term( $name, $taxonomy );
				if ( $term_id <= 0 ) {
					continue;
				}
				if ( in_array( $term_id, $current_ids, true ) || in_array( $term_id, $new_ids, true ) ) {
					continue;
				}
				$new_ids[] = $term_id;
			}
		}

		$names_after = $current_names;
		$added_here  = array();
		if ( $new_ids !== array() ) {
			$union = array_values( array_unique( array_merge( $current_ids, $new_ids ) ) );
			$set   = wp_set_object_terms( $product_id, $union, $taxonomy );
			if ( ! is_wp_error( $set ) ) {
				$after = studio_object_terms( $product_id, $taxonomy );
				if ( ! is_wp_error( $after ) ) {
					$names_after = array();
					foreach ( $after as $term ) {
						$names_after[] = (string) $term->name;
						if ( in_array( (int) $term->term_id, $new_ids, true ) ) {
							$added_here[] = (string) $term->name;
						}
					}
				}
			}
		}

		$report['kept'][ $level ]   = $current_names;
		$report['names'][ $level ]  = $names_after;
		$report['counts'][ $level ] = count( $names_after );
		$report['kept_count']      += count( $current_names );
		foreach ( $added_here as $label ) {
			$report['added'][] = $level . ': ' . $label;
		}
	}

	$report['added_count'] = count( $report['added'] );
	return $report;
}

/**
 * Distinct non-empty names for one fitment level. Rows are not crossed into vehicles.
 *
 * @param array<int,mixed> $fitment
 * @return string[]
 */
/**
 * Persist aligned application rows for the fitment index (union terms stay on the product).
 *
 * @param array<int,mixed> $fitment
 */
function studio_store_fitment_applications( int $product_id, array $fitment ): void {
	if ( $product_id <= 0 || $fitment === array() ) {
		return;
	}
	$existing = get_post_meta( $product_id, '_ydu_fitment_applications', true );
	if ( ! is_array( $existing ) ) {
		$existing = array();
	}
	$seen   = array();
	$merged = array();
	foreach ( array_merge( $existing, $fitment ) as $row ) {
		if ( ! is_array( $row ) ) {
			continue;
		}
		$key = wp_json_encode( $row );
		if ( isset( $seen[ $key ] ) ) {
			continue;
		}
		$seen[ $key ] = true;
		$merged[]     = $row;
	}
	update_post_meta( $product_id, '_ydu_fitment_applications', $merged );
}

function studio_incoming_names( array $fitment, string $level ): array {
	$names = array();
	foreach ( $fitment as $row ) {
		if ( ! is_array( $row ) ) {
			continue;
		}
		$raw = $row[ $level ] ?? '';
		if ( is_array( $raw ) || is_object( $raw ) ) {
			continue;
		}
		$val = trim( (string) $raw );
		if ( $val !== '' ) {
			$names[ $val ] = $val;
		}
	}
	return array_values( $names );
}

/**
 * Terms already assigned to the product. WP_Error means the caller must not write.
 *
 * @return WP_Term[]|WP_Error
 */
function studio_object_terms( int $product_id, string $taxonomy ) {
	if ( $product_id <= 0 || ! taxonomy_exists( $taxonomy ) ) {
		return array();
	}
	$terms = wp_get_object_terms(
		$product_id,
		$taxonomy,
		array(
			'fields'  => 'all',
			'orderby' => 'name',
		)
	);
	if ( is_wp_error( $terms ) ) {
		return $terms;
	}
	if ( ! is_array( $terms ) ) {
		return array();
	}
	$out = array();
	foreach ( $terms as $term ) {
		if ( $term instanceof WP_Term ) {
			$out[] = $term;
		}
	}
	return $out;
}

/**
 * Find or create one attribute term. Returns 0 when the taxonomy cannot take it.
 */
function studio_ensure_term( string $name, string $taxonomy ): int {
	$name = trim( $name );
	if ( $name === '' || ! taxonomy_exists( $taxonomy ) ) {
		return 0;
	}
	$term = term_exists( $name, $taxonomy );
	if ( ! $term ) {
		$term = wp_insert_term( $name, $taxonomy );
	}
	if ( is_wp_error( $term ) ) {
		$term = term_exists( $name, $taxonomy );
	}
	if ( is_wp_error( $term ) || ! $term ) {
		return 0;
	}
	if ( is_array( $term ) ) {
		return (int) ( $term['term_id'] ?? 0 );
	}
	return (int) $term;
}

/**
 * @param string[] $skus
 * @param string[] $missing
 * @return int[]
 */
function studio_ids_for_skus( array $skus, array &$missing ): array {
	$ids = array();
	foreach ( $skus as $sku ) {
		$sku = trim( (string) $sku );
		if ( $sku === '' ) {
			continue;
		}
		$id = (int) wc_get_product_id_by_sku( $sku );
		if ( $id ) {
			$ids[] = $id;
		} else {
			$missing[] = $sku;
		}
	}
	return $ids;
}

/**
 * Keep the link on both products. Local shop only; the caller already refused other hosts.
 *
 * @param int[] $wanted
 */
function studio_mirror_links( int $pid, array $wanted, string $kind ): void {
	$meta_key = 'upsell' === $kind ? '_upsell_ids' : '_crosssell_ids';
	$getter   = 'upsell' === $kind ? 'get_upsell_ids' : 'get_cross_sell_ids';
	$setter   = 'upsell' === $kind ? 'set_upsell_ids' : 'set_cross_sell_ids';
	$wanted   = array_values( array_unique( array_map( 'intval', $wanted ) ) );
	$all      = wc_get_products(
		array(
			'limit'  => -1,
			'return' => 'ids',
			'status' => array( 'publish', 'draft', 'pending', 'private' ),
		)
	);
	foreach ( $all as $oid ) {
		$oid = (int) $oid;
		if ( $oid === $pid ) {
			continue;
		}
		$current = array_map( 'intval', (array) get_post_meta( $oid, $meta_key, true ) );
		$should  = in_array( $oid, $wanted, true );
		$has     = in_array( $pid, $current, true );
		if ( $should === $has ) {
			continue;
		}
		$product = wc_get_product( $oid );
		if ( ! $product ) {
			continue;
		}
		$ids = array_map( 'intval', (array) $product->$getter() );
		if ( $should ) {
			$ids[] = $pid;
		} else {
			$ids = array_values( array_diff( $ids, array( $pid ) ) );
		}
		$product->$setter( array_values( array_unique( $ids ) ) );
		$product->save();
	}
}
