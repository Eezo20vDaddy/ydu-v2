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
		'eye'      => '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
		'car'      => '<path d="M5 11l1.5-4.5A2 2 0 0 1 8.4 5h7.2a2 2 0 0 1 1.9 1.5L19 11"/><rect x="3" y="11" width="18" height="6" rx="1.5"/><circle cx="7" cy="17" r="1.6"/><circle cx="17" cy="17" r="1.6"/>',
		'image'    => '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
		'arrow'    => '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
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
function ydu_logo( int $height = 0 ): string {
	if ( has_custom_logo() ) {
		return get_custom_logo();
	}
	$fallback = 'https://ydu.com.au/wp-content/uploads/2024/11/banner-300x103.png';
	if ( $height > 0 ) {
		return sprintf(
			'<img class="custom-logo" src="%1$s" alt="%2$s" width="300" height="103" style="height:%3$dpx;width:auto">',
			esc_url( $fallback ),
			esc_attr( get_bloginfo( 'name' ) ),
			(int) $height
		);
	}
	return sprintf(
		'<img class="custom-logo" src="%1$s" alt="%2$s" width="300" height="103">',
		esc_url( $fallback ),
		esc_attr( get_bloginfo( 'name' ) )
	);
}

/** WooCommerce cart item count (0 when Woo/cart unavailable). */
function ydu_cart_count(): int {
	if ( function_exists( 'WC' ) && WC()->cart ) {
		return (int) WC()->cart->get_cart_contents_count();
	}
	return 0;
}

/**
 * Saved-parts count for the logged-in customer. Guests are filled in by the
 * browser after load, because the page cache must not store one visitor's list.
 */
function ydu_wishlist_count(): int {
	return ydu_saved_count( 'wishlist' );
}

/** Compare-list count for the logged-in customer. Guests are filled in by the browser. */
function ydu_compare_count(): int {
	return ydu_saved_count( 'compare' );
}

/**
 * Icon name for a product category, matched on slug/name keywords.
 * Falls back to a generic grid icon.
 */
function ydu_category_icon_name( string $slug, string $name = '' ): string {
	$haystack = strtolower( $slug . ' ' . $name );
	$map = array(
		'engine'       => 'cog',
		'gasket'       => 'layers',
		'seal'         => 'layers',
		'filter'       => 'filter',
		'cool'         => 'snow',
		'radiator'     => 'snow',
		'transmission' => 'cog',
		'clutch'       => 'cog',
		'electric'     => 'bolt',
		'sensor'       => 'bolt',
		'fuel'         => 'droplet',
		'suspension'   => 'activity',
		'brake'        => 'disc',
		'body'         => 'truck',
		'performance'  => 'gauge',
		'interior'     => 'seat',
	);
	foreach ( $map as $needle => $icon ) {
		if ( str_contains( $haystack, $needle ) ) {
			return $icon;
		}
	}
	return 'grid';
}

/** Extended icon set for category tiles (returns trusted inline SVG). */
function ydu_category_icon( string $icon, int $size = 26 ): string {
	$paths = array(
		'cog'      => '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
		'layers'   => '<polygon points="12 2 22 8.5 12 15 2 8.5 12 2"/><polyline points="2 13 12 19.5 22 13"/>',
		'filter'   => '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
		'snow'     => '<line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="4.9" y1="4.9" x2="19.1" y2="19.1"/><line x1="19.1" y1="4.9" x2="4.9" y2="19.1"/>',
		'bolt'     => '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
		'droplet'  => '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
		'activity' => '<path d="M5 21c4-1.5 2-5 6-6.5S17 9 17 9"/><circle cx="18.5" cy="5.5" r="2.5"/><circle cx="5" cy="20.5" r="1.8"/>',
		'disc'     => '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>',
		'truck'    => '<path d="M3 13l1.5-4.5A2 2 0 0 1 6.4 7h11.2a2 2 0 0 1 1.9 1.5L21 13"/><rect x="2" y="13" width="20" height="5" rx="1.5"/><circle cx="6.5" cy="18" r="1.8"/><circle cx="17.5" cy="18" r="1.8"/>',
		'gauge'    => '<path d="M12 20a8 8 0 1 1 8-8"/><path d="M12 12l5-3"/>',
		'seat'     => '<path d="M7 18V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v12"/><path d="M5 18h12a2 2 0 0 1 2 2v1H5a2 2 0 0 1-2-2v-7"/>',
		'grid'     => '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
	);
	$inner = $paths[ $icon ] ?? $paths['grid'];
	return sprintf(
		'<svg width="%1$d" height="%1$d" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%2$s</svg>',
		$size,
		$inner
	);
}

/** Rounded published-product count for the hero stat, e.g. "300+". */
function ydu_catalog_count_label(): string {
	$counts = wp_count_posts( 'product' );
	$n      = isset( $counts->publish ) ? (int) $counts->publish : 0;
	if ( $n < 50 ) {
		return (string) max( $n, 0 );
	}
	$rounded = (int) ( floor( $n / 50 ) * 50 );
	return number_format_i18n( $rounded ) . '+';
}

/**
 * Most specific product_cat label for product cards (deepest assigned term).
 *
 * @param int $product_id Product post ID.
 */
function ydu_product_card_category_label( int $product_id ): string {
	$terms = get_the_terms( $product_id, 'product_cat' );
	if ( ! $terms || is_wp_error( $terms ) ) {
		return '';
	}

	$assigned_ids = array_map( 'intval', wp_list_pluck( $terms, 'term_id' ) );
	$leaves       = array();

	foreach ( $terms as $term ) {
		$is_ancestor = false;
		foreach ( $assigned_ids as $other_id ) {
			if ( (int) $term->term_id === $other_id ) {
				continue;
			}
			if ( term_is_ancestor_of( (int) $term->term_id, $other_id, 'product_cat' ) ) {
				$is_ancestor = true;
				break;
			}
		}
		if ( ! $is_ancestor ) {
			$leaves[] = array(
				'term'  => $term,
				'depth' => count( get_ancestors( $term->term_id, 'product_cat', 'taxonomy' ) ),
			);
		}
	}

	if ( empty( $leaves ) ) {
		return $terms[0]->name;
	}

	$max_depth = max( array_column( $leaves, 'depth' ) );
	foreach ( $terms as $term ) {
		foreach ( $leaves as $leaf ) {
			if ( (int) $leaf['term']->term_id === (int) $term->term_id && $leaf['depth'] === $max_depth ) {
				return $term->name;
			}
		}
	}

	return $leaves[0]['term']->name;
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
