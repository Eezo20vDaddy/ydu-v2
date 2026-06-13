<?php
/**
 * Presentation helpers for the YDU theme shell.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

/**
 * Inline SVG icon set (stroke icons matching the Variant C mockup).
 * Returns escaped, fixed markup — safe to echo.
 */
function ydu_icon( string $name, int $size = 21 ): string {
	$paths = array(
		'phone'    => '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/>',
		'truck'    => '<rect x="1" y="3" width="15" height="13" rx="1"/><path d="M16 8h4l3 3v5h-7V8z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
		'menu'     => '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
		'close'    => '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
		'user'     => '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
		'heart'    => '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>',
		'compare'  => '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
		'cart'     => '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>',
		'search'   => '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
		'car'      => '<path d="M5 11l1.5-4.5A2 2 0 0 1 8.4 5h7.2a2 2 0 0 1 1.9 1.5L19 11"/><rect x="3" y="11" width="18" height="6" rx="1.5"/><circle cx="7" cy="17" r="1.6"/><circle cx="17" cy="17" r="1.6"/>',
	);
	$inner = $paths[ $name ] ?? '';
	$sw    = ( 'search' === $name ) ? '2.2' : '2';
	return sprintf(
		'<svg width="%1$d" height="%1$d" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="%2$s" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%3$s</svg>',
		$size,
		esc_attr( $sw ),
		$inner // static, trusted markup
	);
}

/**
 * Site logo: custom logo when set, otherwise the YDU banner.
 */
function ydu_logo( int $height = 40 ): string {
	if ( has_custom_logo() ) {
		return get_custom_logo();
	}
	$fallback = 'https://ydu.com.au/wp-content/uploads/2024/11/banner-300x103.png';
	return sprintf(
		'<img class="custom-logo" src="%1$s" alt="%2$s" width="300" height="103" style="height:%3$dpx;width:auto">',
		esc_url( $fallback ),
		esc_attr( get_bloginfo( 'name' ) ),
		(int) $height
	);
}

/** WooCommerce cart item count (0 when Woo/cart unavailable). */
function ydu_cart_count(): int {
	if ( function_exists( 'WC' ) && WC()->cart ) {
		return (int) WC()->cart->get_cart_contents_count();
	}
	return 0;
}

/** WPClever wishlist count, or null when the plugin is inactive. */
function ydu_wishlist_count(): ?int {
	if ( function_exists( 'woosw_get_count' ) ) {
		return (int) woosw_get_count();
	}
	return null;
}

/** WPClever compare count, or null when the plugin is inactive. */
function ydu_compare_count(): ?int {
	if ( function_exists( 'woosc_get_count' ) ) {
		return (int) woosc_get_count();
	}
	return null;
}

/** Top-level product categories for the search scope dropdown. */
function ydu_search_categories(): array {
	if ( ! taxonomy_exists( 'product_cat' ) ) {
		return array();
	}
	$terms = get_terms( array(
		'taxonomy'   => 'product_cat',
		'hide_empty' => true,
		'parent'     => 0,
		'orderby'    => 'name',
	) );
	return is_wp_error( $terms ) ? array() : $terms;
}
