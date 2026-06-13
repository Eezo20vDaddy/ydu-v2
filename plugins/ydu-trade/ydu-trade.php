<?php
/**
 * Plugin Name:       YDU Trade Pricing
 * Description:       Per-customer "last price paid" trade pricing for YDU PARTS. Trade customers see their own individual price per item (the last price they actually paid); everyone else sees standard pricing. Prices are stored per (customer, product) and written by an authenticated ingestion endpoint — the entry point for the Zoho feedback loop (Zoho edits the invoiced line price → syncs back here → used next time). This is a DISPLAY layer: it never overwrites the product's Zoho-synced base price.
 * Version:           0.1.0
 * Requires at least: 6.5
 * Requires PHP:      8.0
 * Author:            YDU PARTS
 * License:           GPL-2.0-or-later
 * Text Domain:       ydu-trade
 *
 * @package ydu-trade
 *
 * STATUS: foundation (CEO decision 2026-06-13). The Zoho feedback SYNC (reading edited
 * line prices out of Zoho and POSTing them to fitment ingestion) is a separate task that
 * needs Zoho API credentials + connector discovery — see spec §5.5. This plugin provides
 * the role, the price store, the display substitution, and the ingestion endpoint the
 * sync will call. Off by default for guests/retail; only logged-in `trade` users with a
 * stored price for an item are affected.
 */

defined( 'ABSPATH' ) || exit;

define( 'YDU_TRADE_VERSION', '0.1.0' );
define( 'YDU_TRADE_DIR', plugin_dir_path( __FILE__ ) );
define( 'YDU_TRADE_ROLE', 'trade' );

require_once YDU_TRADE_DIR . 'includes/class-ydu-trade-store.php';
require_once YDU_TRADE_DIR . 'includes/class-ydu-trade-pricing.php';
require_once YDU_TRADE_DIR . 'includes/class-ydu-trade-rest.php';

register_activation_hook( __FILE__, 'ydu_trade_activate' );
function ydu_trade_activate(): void {
	YDU_Trade_Store::install_table();
	add_role( YDU_TRADE_ROLE, __( 'Trade', 'ydu-trade' ), array( 'read' => true ) );
}

add_action( 'plugins_loaded', static function (): void {
	// Ensure the table exists even if the plugin was copied in without activation
	// (e.g. via .wp-env.json mount); cheap dbDelta is idempotent.
	YDU_Trade_Store::maybe_upgrade();
	if ( ! get_role( YDU_TRADE_ROLE ) ) {
		add_role( YDU_TRADE_ROLE, __( 'Trade', 'ydu-trade' ), array( 'read' => true ) );
	}
	YDU_Trade_Pricing::init();
} );

add_action( 'rest_api_init', static function (): void {
	( new YDU_Trade_REST() )->register_routes();
} );

/** True when the current (or given) user is a trade customer. */
function ydu_trade_is_trade_user( int $user_id = 0 ): bool {
	$user = $user_id ? get_userdata( $user_id ) : wp_get_current_user();
	return $user && in_array( YDU_TRADE_ROLE, (array) $user->roles, true );
}
