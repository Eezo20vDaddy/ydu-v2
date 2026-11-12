<?php
/**
 * Map WooCommerce linked products in the product import/export tool.
 *
 * Upsells, cross-sells, and grouped children are mapped by SKU. A numeric
 * token that is already a product ID is left as that ID.
 *
 * @package ydu-fitment
 */

defined( 'ABSPATH' ) || exit;

/**
 * @param array<string,mixed> $fields
 * @return array<string,mixed>
 */
function ydu_linked_product_mapping_fields( array $fields ): array {
	$linked = array(
		'upsell_ids'    => array(
			'title'          => 'Linked products: Upsells',
			'description'    => 'Upsell SKUs, separated by |. A product ID is also accepted.',
			'similar_fields' => array( 'Upsells', 'Upsell IDs', 'Upsell SKUs', 'Linked upsells', 'Related products: Upsell IDs' ),
		),
		'crosssell_ids' => array(
			'title'          => 'Linked products: Cross-sells',
			'description'    => 'Cross-sell SKUs, separated by |. A product ID is also accepted.',
			'similar_fields' => array( 'Cross-sells', 'Crosssell IDs', 'Cross-sell SKUs', 'Linked cross-sells', 'Related products: Crosssell IDs' ),
		),
		'children'      => array(
			'title'          => 'Linked products: Grouped children',
			'description'    => 'Grouped product child SKUs, separated by |. A product ID is also accepted.',
			'similar_fields' => array( 'Grouped products', 'Children', 'Child SKUs', 'Linked products', 'Child product ID' ),
		),
	);

	foreach ( $linked as $key => $copy ) {
		if ( ! isset( $fields[ $key ] ) ) {
			continue;
		}
		if ( is_array( $fields[ $key ] ) ) {
			$fields[ $key ]['title']          = $copy['title'];
			$fields[ $key ]['description']    = $copy['description'];
			$fields[ $key ]['field_type']     = 'alternates';
			$fields[ $key ]['similar_fields'] = $copy['similar_fields'];
		} else {
			$fields[ $key ] = $copy['title'];
		}
	}

	return $fields;
}

/**
 * @param array<string,mixed> $fields
 * @param string              $base
 * @return array<string,mixed>
 */
function ydu_linked_product_alter_mapping_fields( $fields, $base ) {
	if ( 'product' !== $base || ! is_array( $fields ) ) {
		return $fields;
	}
	return ydu_linked_product_mapping_fields( $fields );
}

add_filter( 'wt_iew_importer_alter_mapping_fields_basic', 'ydu_linked_product_alter_mapping_fields', 20, 2 );
add_filter( 'wt_iew_exporter_alter_mapping_fields_basic', 'ydu_linked_product_alter_mapping_fields', 20, 2 );

/**
 * Split a linked-product cell on | or comma.
 *
 * @return string[]
 */
function ydu_linked_product_tokens( string $raw ): array {
	$raw = trim( $raw );
	if ( '' === $raw ) {
		return array();
	}
	$parts = preg_split( '/[|,]/', trim( $raw, "[]" ) );
	$out   = array();
	foreach ( $parts as $part ) {
		$part = trim( $part, " \t\n\r\0\x0B\"'" );
		if ( '' !== $part ) {
			$out[] = $part;
		}
	}
	return $out;
}

/**
 * Export linked-product columns as SKUs.
 *
 * @param array<string,mixed> $row
 * @return array<string,mixed>
 */
function ydu_linked_product_export_skus( $row ) {
	if ( ! is_array( $row ) ) {
		return $row;
	}
	foreach ( array( 'upsell_ids', 'crosssell_ids', 'children', '_upsell_ids', '_crosssell_ids', '_children' ) as $column ) {
		if ( ! isset( $row[ $column ] ) || ! is_scalar( $row[ $column ] ) ) {
			continue;
		}
		$skus = array();
		foreach ( ydu_linked_product_tokens( (string) $row[ $column ] ) as $token ) {
			if ( ctype_digit( $token ) ) {
				$sku = (string) get_post_meta( (int) $token, '_sku', true );
				$skus[] = '' !== $sku ? $sku : $token;
			} else {
				$skus[] = $token;
			}
		}
		$row[ $column ] = implode( '|', $skus );
	}
	return $row;
}

add_filter( 'wt_batch_product_export_row_data', 'ydu_linked_product_export_skus', 20 );

/**
 * Turn mapped SKUs into product IDs before the importer stores them.
 *
 * @param array<string,mixed> $mapped
 * @return array<string,mixed>
 */
function ydu_linked_product_import_ids( $mapped ) {
	if ( ! is_array( $mapped ) ) {
		return $mapped;
	}
	foreach ( array( 'upsell_ids', '_upsell_ids', 'crosssell_ids', '_crosssell_ids', 'children', '_children' ) as $column ) {
		if ( empty( $mapped[ $column ] ) || ! is_scalar( $mapped[ $column ] ) ) {
			continue;
		}
		$ids = array();
		foreach ( ydu_linked_product_tokens( (string) $mapped[ $column ] ) as $token ) {
			if ( ctype_digit( $token ) && 'product' === get_post_type( (int) $token ) ) {
				$ids[] = $token;
				continue;
			}
			$found = function_exists( 'wc_get_product_id_by_sku' ) ? (int) wc_get_product_id_by_sku( $token ) : 0;
			if ( $found ) {
				$ids[] = (string) $found;
			}
		}
		$mapped[ $column ] = implode( '|', $ids );
	}
	return $mapped;
}

add_filter( 'wt_woocommerce_product_importer_pre_parse_data', 'ydu_linked_product_import_ids', 20 );

/**
 * After an import links part X to part Y, link Y back to X.
 *
 * @param mixed $product
 */
function ydu_linked_product_mirror_back( $product ): void {
	if ( ! $product instanceof WC_Product ) {
		return;
	}
	$pid = (int) $product->get_id();
	$pairs = array(
		'upsell' => array( $product->get_upsell_ids(), 'get_upsell_ids', 'set_upsell_ids' ),
		'cross'  => array( $product->get_cross_sell_ids(), 'get_cross_sell_ids', 'set_cross_sell_ids' ),
	);
	foreach ( $pairs as $pair ) {
		list( $ids, $getter, $setter ) = $pair;
		foreach ( array_map( 'intval', (array) $ids ) as $other_id ) {
			if ( $other_id <= 0 || $other_id === $pid ) {
				continue;
			}
			$other = wc_get_product( $other_id );
			if ( ! $other ) {
				continue;
			}
			$theirs = array_map( 'intval', (array) $other->$getter() );
			if ( in_array( $pid, $theirs, true ) ) {
				continue;
			}
			$theirs[] = $pid;
			$other->$setter( $theirs );
			$other->save();
		}
	}
}

add_action( 'wt_woocommerce_product_import_inserted_product_object', 'ydu_linked_product_mirror_back', 20 );
