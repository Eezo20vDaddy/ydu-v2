<?php
/**
 * WooCommerce integration. Shop layout customisation lands with tasks 2.1-2.4;
 * this file holds only the baseline wiring the scaffold needs.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

// Default WooCommerce stylesheets stay enqueued; the theme restyles Woo output
// via theme.json tokens + style.scss. Shop cards: woocommerce/content-product.php.

/**
 * Storefront prices: currency symbol before the amount (e.g. $2,087.23).
 * Runs after currency-switcher plugins so local/catalog display stays consistent.
 */
add_filter( 'option_woocommerce_currency_pos', 'ydu_storefront_currency_pos_left', 10001 );
function ydu_storefront_currency_pos_left( $position ) {
	if ( is_admin() && ! wp_doing_ajax() ) {
		return $position;
	}
	return 'left';
}

add_filter( 'woocommerce_price_format', 'ydu_storefront_price_format', 10001, 2 );
function ydu_storefront_price_format( $format, $currency_pos ) {
	if ( is_admin() && ! wp_doing_ajax() ) {
		return $format;
	}
	switch ( $currency_pos ) {
		case 'left':
			return '%1$s%2$s';
		case 'right':
			return '%2$s%1$s';
		case 'left_space':
			return '%1$s&nbsp;%2$s';
		case 'right_space':
			return '%2$s&nbsp;%1$s';
	}
	return $format;
}

/**
 * "Fits these vehicles" panel on the single product page, built from the
 * product's fitment attribute terms (pa_make > pa_model > pa_submodel >
 * pa_variant). Read-only display; links to the filtered catalogue.
 */
add_action( 'woocommerce_after_single_product_summary', 'ydu_fitment_panel', 5 );
function ydu_fitment_panel(): void {
	global $product;
	if ( ! $product instanceof WC_Product ) {
		return;
	}

	$levels = array(
		'pa_make'     => array( 'label' => __( 'Make', 'ydu' ), 'filter' => 'filter_make' ),
		'pa_model'    => array( 'label' => __( 'Model', 'ydu' ), 'filter' => 'filter_model' ),
		'pa_submodel' => array( 'label' => __( 'Submodel', 'ydu' ), 'filter' => 'filter_submodel' ),
		'pa_variant'  => array( 'label' => __( 'Variant', 'ydu' ), 'filter' => 'filter_variant' ),
	);

	$rows = array();
	foreach ( $levels as $taxonomy => $meta ) {
		$terms = get_the_terms( $product->get_id(), $taxonomy );
		if ( $terms && ! is_wp_error( $terms ) ) {
			$rows[ $taxonomy ] = array( 'meta' => $meta, 'terms' => $terms );
		}
	}

	if ( empty( $rows ) ) {
		return;
	}

	$shop = wc_get_page_permalink( 'shop' );
	echo '<section class="ydu-fitment-panel" aria-labelledby="ydu-fit-h">';
	echo '<h2 id="ydu-fit-h">' . esc_html__( 'Fits these vehicles', 'ydu' ) . '</h2>';
	echo '<p class="ydu-fitment-help">' . esc_html__( 'This part is listed as fitting the following VW / Audi / VAG applications. Always cross-check your part number before ordering.', 'ydu' ) . '</p>';
	echo '<dl class="ydu-fitment-list">';
	foreach ( $rows as $row ) {
		echo '<dt>' . esc_html( $row['meta']['label'] ) . '</dt><dd>';
		$chips = array();
		foreach ( $row['terms'] as $term ) {
			$url = add_query_arg( $row['meta']['filter'], $term->slug, $shop );
			$chips[] = sprintf( '<a class="ydu-fit-chip" href="%s">%s</a>', esc_url( $url ), esc_html( $term->name ) );
		}
		echo wp_kses_post( implode( ' ', $chips ) );
		echo '</dd>';
	}
	echo '</dl>';
	echo '</section>';
}
