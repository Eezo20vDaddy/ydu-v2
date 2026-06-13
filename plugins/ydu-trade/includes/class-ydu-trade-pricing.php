<?php
/**
 * Display layer: substitute a trade customer's stored individual price for a
 * product, falling back to the standard price when none is stored. This is a
 * read/display filter only — it never writes to or overrides the product's
 * stored (Zoho-synced) base price.
 *
 * @package ydu-trade
 */

defined( 'ABSPATH' ) || exit;

class YDU_Trade_Pricing {

	public static function init(): void {
		// Apply only on the front end for logged-in trade users.
		add_filter( 'woocommerce_product_get_price', array( __CLASS__, 'filter_price' ), 20, 2 );
		add_filter( 'woocommerce_product_variation_get_price', array( __CLASS__, 'filter_price' ), 20, 2 );
		// Ensure cart uses the trade price too.
		add_action( 'woocommerce_before_calculate_totals', array( __CLASS__, 'apply_cart_prices' ), 20 );
	}

	/**
	 * @param string     $price   The product's current price.
	 * @param WC_Product $product
	 * @return string
	 */
	public static function filter_price( $price, $product ) {
		$trade = self::trade_price_for( $product );
		return null === $trade ? $price : (string) $trade;
	}

	/** Resolve the current trade user's stored price for a product, or null. */
	public static function trade_price_for( $product ): ?float {
		if ( is_admin() && ! wp_doing_ajax() ) {
			return null;
		}
		$user_id = get_current_user_id();
		if ( $user_id <= 0 || ! function_exists( 'ydu_trade_is_trade_user' ) || ! ydu_trade_is_trade_user( $user_id ) ) {
			return null;
		}
		if ( ! $product instanceof WC_Product ) {
			return null;
		}
		// For variations, fall back to the variation's own id then its parent.
		$pid   = $product->get_id();
		$price = YDU_Trade_Store::get_price( $user_id, $pid );
		if ( null === $price && $product->get_parent_id() ) {
			$price = YDU_Trade_Store::get_price( $user_id, $product->get_parent_id() );
		}
		return $price;
	}

	/** Apply stored trade prices to cart line items. */
	public static function apply_cart_prices( $cart ): void {
		if ( is_admin() && ! wp_doing_ajax() ) {
			return;
		}
		if ( ! function_exists( 'ydu_trade_is_trade_user' ) || ! ydu_trade_is_trade_user() ) {
			return;
		}
		foreach ( $cart->get_cart() as $item ) {
			if ( empty( $item['data'] ) || ! $item['data'] instanceof WC_Product ) {
				continue;
			}
			$trade = self::trade_price_for( $item['data'] );
			if ( null !== $trade ) {
				$item['data']->set_price( (string) $trade );
			}
		}
	}
}
