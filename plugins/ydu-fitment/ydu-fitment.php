<?php
/**
 * Plugin Name:       YDU Fitment
 * Plugin URI:        https://ydu.com.au
 * Description:       Vehicle finder for YDU PARTS. Searchable year, make, model, submodel, variant and engine code over the existing flat pa_* attributes. Any box filters the others. Provides fitment/v1 and a finder widget. No data migration.
 * Version:           0.1.0
 * Requires at least: 6.5
 * Requires PHP:      8.0
 * Author:            YDU PARTS
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       ydu-fitment
 *
 * @package ydu-fitment
 */

defined( 'ABSPATH' ) || exit;

define( 'YDU_FITMENT_VERSION', '0.1.0' );
define( 'YDU_FITMENT_FILE', __FILE__ );
define( 'YDU_FITMENT_DIR', plugin_dir_path( __FILE__ ) );
define( 'YDU_FITMENT_URL', plugin_dir_url( __FILE__ ) );

/**
 * Ordered cascade levels: attribute taxonomy => WooCommerce layered-nav query var.
 * Order is year, make, model, submodel, variant, engine code. Any selected level
 * filters every other level. This map is the source of truth for REST, the finder, and tests.
 */
function ydu_fitment_levels(): array {
	return array(
		'year'        => array( 'taxonomy' => 'pa_year_alt', 'filter' => 'filter_year_alt', 'label' => 'Year' ),
		'make'        => array( 'taxonomy' => 'pa_make', 'filter' => 'filter_make', 'label' => 'Make' ),
		'model'       => array( 'taxonomy' => 'pa_model', 'filter' => 'filter_model', 'label' => 'Model' ),
		'submodel'    => array( 'taxonomy' => 'pa_submodel', 'filter' => 'filter_submodel', 'label' => 'Submodel' ),
		'variant'     => array( 'taxonomy' => 'pa_variant', 'filter' => 'filter_variant', 'label' => 'Variant' ),
		'engine_code' => array( 'taxonomy' => 'pa_engine_code', 'filter' => 'filter_engine_code', 'label' => 'Engine Code' ),
	);
}

require_once YDU_FITMENT_DIR . 'includes/class-ydu-fitment-cascade.php';
require_once YDU_FITMENT_DIR . 'includes/class-ydu-fitment-rest.php';
require_once YDU_FITMENT_DIR . 'includes/class-ydu-fitment-widget.php';
require_once YDU_FITMENT_DIR . 'includes/class-ydu-linked-products-io.php';

add_action( 'rest_api_init', static function (): void {
	( new YDU_Fitment_REST() )->register_routes();
} );

add_action( 'init', static function (): void {
	YDU_Fitment_Widget::init();
} );

// Declare HPOS compatibility (no order data access here, but be explicit).
add_action( 'before_woocommerce_init', static function (): void {
	if ( class_exists( \Automattic\WooCommerce\Utilities\FeaturesUtil::class ) ) {
		\Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility( 'custom_order_tables', YDU_FITMENT_FILE, true );
	}
} );
