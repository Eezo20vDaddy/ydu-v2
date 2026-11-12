<?php
/**
 * Saved parts, compare, and quick view.
 *
 * Replaces the WPC Smart Wishlist, Compare, and Quick View plugins.
 * The lists live in the browser so a cached page cannot show another
 * visitor's parts. Logged-in customers also get a copy on their account.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

const YDU_COMPARE_MAX  = 4;
const YDU_WISHLIST_MAX = 100;

/**
 * @param string $list wishlist|compare.
 */
function ydu_saved_count( string $list ): int {
	if ( ! is_user_logged_in() ) {
		return 0;
	}
	$ids = get_user_meta( get_current_user_id(), 'ydu_' . $list, true );
	return is_array( $ids ) ? count( ydu_sanitize_ids( $ids, $list ) ) : 0;
}

/**
 * @param array<int, mixed> $ids Raw ids.
 * @param string            $list wishlist|compare.
 * @return array<int, int>
 */
function ydu_sanitize_ids( array $ids, string $list ): array {
	$clean = array();
	foreach ( $ids as $id ) {
		$id = absint( $id );
		if ( $id && 'product' === get_post_type( $id ) && 'publish' === get_post_status( $id ) ) {
			$clean[] = $id;
		}
	}
	$clean = array_values( array_unique( $clean ) );
	$max   = 'compare' === $list ? YDU_COMPARE_MAX : YDU_WISHLIST_MAX;
	return array_slice( $clean, 0, $max );
}

/**
 * Save / compare / quick-view controls for one product.
 */
function ydu_list_actions( WC_Product $product, string $context = 'card' ): void {
	$id      = $product->get_id();
	$labeled = 'single' === $context;
	$items   = array(
		'wishlist' => array(
			'icon'  => 'heart',
			'label' => __( 'Save', 'ydu' ),
		),
		'compare'  => array(
			'icon'  => 'compare',
			'label' => __( 'Compare', 'ydu' ),
		),
	);
	echo '<div class="ydu-actions' . ( $labeled ? ' ydu-actions--single' : '' ) . '">';
	foreach ( $items as $list => $item ) {
		printf(
			'<button type="button" class="ydu-action" data-ydu-list="%1$s" data-product-id="%2$d" aria-pressed="false" aria-label="%3$s">%4$s%5$s</button>',
			esc_attr( $list ),
			$id,
			esc_attr( $item['label'] ),
			ydu_icon( $item['icon'], 16 ), // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
			$labeled ? '<span>' . esc_html( $item['label'] ) . '</span>' : ''
		);
	}
	printf(
		'<button type="button" class="ydu-action" data-ydu-quick="%1$d" aria-label="%2$s">%3$s%4$s</button>',
		$id,
		esc_attr__( 'Quick view', 'ydu' ),
		ydu_icon( 'eye', 16 ), // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
		$labeled ? '<span>' . esc_html__( 'Quick view', 'ydu' ) . '</span>' : ''
	);
	echo '</div>';
}

add_action( 'woocommerce_after_add_to_cart_form', 'ydu_single_list_actions', 15 );
function ydu_single_list_actions(): void {
	global $product;
	if ( $product instanceof WC_Product ) {
		ydu_list_actions( $product, 'single' );
	}
}

add_action( 'wp_enqueue_scripts', 'ydu_lists_script_data', 20 );
function ydu_lists_script_data(): void {
	if ( ! wp_script_is( 'ydu-frontend', 'enqueued' ) ) {
		return;
	}
	wp_localize_script(
		'ydu-frontend',
		'yduLists',
		array(
			'root'         => esc_url_raw( rest_url( 'ydu/v1/lists' ) ),
			'store'        => esc_url_raw( rest_url( 'wc/store/v1/products' ) ),
			'nonce'        => wp_create_nonce( 'wp_rest' ),
			'loggedIn'     => is_user_logged_in(),
			'compareMax'   => YDU_COMPARE_MAX,
			'wishlistMax'  => YDU_WISHLIST_MAX,
			'compareFull'  => __( 'Compare holds 4 parts. Remove one first.', 'ydu' ),
			'wishlistFull' => __( 'Saved parts is full (100).', 'ydu' ),
		)
	);
}

add_action( 'rest_api_init', 'ydu_register_list_routes' );
function ydu_register_list_routes(): void {
	register_rest_route(
		'ydu/v1',
		'/lists',
		array(
			array(
				'methods'             => 'GET',
				'callback'            => 'ydu_rest_get_lists',
				'permission_callback' => 'ydu_lists_permission',
			),
			array(
				'methods'             => 'POST',
				'callback'            => 'ydu_rest_save_lists',
				'permission_callback' => 'ydu_lists_permission',
			),
		)
	);
}

function ydu_lists_permission( WP_REST_Request $request ): bool {
	$nonce = $request->get_header( 'X-WP-Nonce' );
	return is_user_logged_in() && (bool) wp_verify_nonce( is_string( $nonce ) ? $nonce : '', 'wp_rest' );
}

function ydu_rest_get_lists(): WP_REST_Response {
	$user = get_current_user_id();
	$out  = array();
	foreach ( array( 'wishlist', 'compare' ) as $list ) {
		$stored    = get_user_meta( $user, 'ydu_' . $list, true );
		$out[ $list ] = ydu_sanitize_ids( is_array( $stored ) ? $stored : array(), $list );
	}
	return new WP_REST_Response( $out );
}

function ydu_rest_save_lists( WP_REST_Request $request ): WP_REST_Response {
	$user = get_current_user_id();
	$body = $request->get_json_params();
	$out  = array();
	foreach ( array( 'wishlist', 'compare' ) as $list ) {
		$raw          = ( is_array( $body ) && isset( $body[ $list ] ) && is_array( $body[ $list ] ) ) ? $body[ $list ] : array();
		$out[ $list ] = ydu_sanitize_ids( $raw, $list );
		update_user_meta( $user, 'ydu_' . $list, $out[ $list ] );
	}
	return new WP_REST_Response( $out );
}

add_filter( 'query_vars', 'ydu_lists_query_var' );
function ydu_lists_query_var( array $vars ): array {
	$vars[] = 'ydu_screen';
	return $vars;
}

add_action( 'init', 'ydu_lists_rewrites' );
function ydu_lists_rewrites(): void {
	add_rewrite_rule( '^wishlist/?$', 'index.php?ydu_screen=wishlist', 'top' );
	add_rewrite_rule( '^compare/?$', 'index.php?ydu_screen=compare', 'top' );
	if ( '1' !== get_option( 'ydu_lists_rewrite' ) ) {
		flush_rewrite_rules( false );
		update_option( 'ydu_lists_rewrite', '1', false );
	}
}

add_filter( 'pre_handle_404', 'ydu_lists_not_404', 10, 2 );
function ydu_lists_not_404( $pre, $query ) {
	unset( $query );
	$screen = get_query_var( 'ydu_screen' );
	if ( 'wishlist' === $screen || 'compare' === $screen ) {
		return true;
	}
	return $pre;
}

add_filter( 'document_title_parts', 'ydu_lists_title' );
function ydu_lists_title( array $parts ): array {
	$screen = get_query_var( 'ydu_screen' );
	if ( 'wishlist' === $screen ) {
		$parts['title'] = __( 'Saved parts', 'ydu' );
	} elseif ( 'compare' === $screen ) {
		$parts['title'] = __( 'Compare parts', 'ydu' );
	}
	return $parts;
}

add_action( 'template_redirect', 'ydu_lists_screen' );
function ydu_lists_screen(): void {
	$screen = get_query_var( 'ydu_screen' );
	if ( 'wishlist' !== $screen && 'compare' !== $screen ) {
		return;
	}
	status_header( 200 );
	get_header();
	$title = 'wishlist' === $screen
		? __( 'Saved parts', 'ydu' )
		: __( 'Compare parts', 'ydu' );
	$empty = 'wishlist' === $screen
		? __( 'No saved parts yet. Use Save on a part to keep it here.', 'ydu' )
		: __( 'Nothing to compare yet. Use Compare on up to 4 parts.', 'ydu' );
	echo '<div class="container ydu-saved" id="yduSaved" data-ydu-screen="' . esc_attr( $screen ) . '">';
	echo '<h1>' . esc_html( $title ) . '</h1>';
	echo '<p class="ydu-saved__status" data-ydu-saved-status hidden></p>';
	echo '<p class="ydu-saved__empty" data-ydu-saved-empty>' . esc_html( $empty ) . '</p>';
	echo '<div class="ydu-saved__list" data-ydu-saved-list></div>';
	echo '</div>';
	get_footer();
	exit;
}
