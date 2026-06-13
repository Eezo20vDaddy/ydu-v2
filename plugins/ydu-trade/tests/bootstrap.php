<?php
/**
 * PHPUnit bootstrap for ydu-trade. Loads WooCommerce (for the pricing-display
 * tests) and this plugin, then installs WC + our table. Store and REST tests do
 * not require WC; pricing tests skip gracefully if WC failed to load.
 *
 * @package ydu-trade
 */

$_tests_dir = getenv( 'WP_TESTS_DIR' ) ?: '/wordpress-phpunit';

require_once dirname( __DIR__ ) . '/vendor/yoast/phpunit-polyfills/phpunitpolyfills-autoload.php';
require_once $_tests_dir . '/includes/functions.php';

tests_add_filter( 'muplugins_loaded', static function (): void {
	$wc = WP_PLUGIN_DIR . '/woocommerce/woocommerce.php';
	if ( file_exists( $wc ) ) {
		require $wc;
	}
	require dirname( __DIR__ ) . '/ydu-trade.php';
} );

require $_tests_dir . '/includes/bootstrap.php';

// Install WooCommerce tables/state if WC is present.
if ( class_exists( 'WC_Install' ) ) {
	WC_Install::install();
	if ( function_exists( 'WC' ) && method_exists( WC(), 'init' ) ) {
		WC()->init();
	}
}

// Ensure our table exists in the test DB.
YDU_Trade_Store::install_table();
