<?php
/**
 * PHPUnit bootstrap for ydu-fitment. Loads the WordPress core test suite and
 * our plugin. WooCommerce is intentionally NOT loaded — the cascade and REST
 * code use only core APIs (taxonomies, WP_Query, get_terms), and the tests
 * register a `product` post type + `pa_*` taxonomies with fixtures, keeping the
 * suite fast and dependency-free.
 *
 * @package ydu-fitment
 */

$_tests_dir = getenv( 'WP_TESTS_DIR' ) ?: '/wordpress-phpunit';

require_once dirname( __DIR__ ) . '/vendor/yoast/phpunit-polyfills/phpunitpolyfills-autoload.php';

require_once $_tests_dir . '/includes/functions.php';

tests_add_filter( 'muplugins_loaded', static function (): void {
	require dirname( __DIR__ ) . '/ydu-fitment.php';
} );

require $_tests_dir . '/includes/bootstrap.php';
