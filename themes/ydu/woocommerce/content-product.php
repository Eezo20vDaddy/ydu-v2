<?php
/**
 * Shop / category archive product cell — delegates to the theme's shared
 * Variant C product card so archives and the home featured grid look identical.
 *
 * Override of woocommerce/content-product.php. Runs inside the products loop
 * (woocommerce_product_loop_start … _end), so the card's <li> is the loop item.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

global $product;
if ( empty( $product ) || ! $product->is_visible() ) {
	return;
}

get_template_part( 'template-parts/product-card' );
