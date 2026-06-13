<?php
/**
 * Plugin Name:       YDU Fitment
 * Plugin URI:        https://ydu.com.au
 * Description:       Vehicle finder for YDU PARTS — cascading Make > Model > Submodel > Variant selector over the existing flat WooCommerce fitment attributes (pa_make, pa_model, pa_submodel, pa_variant). Provides fitment/v1 REST endpoints and an Interactivity-API finder widget. Replaces the legacy "YDU WooCommerce Filter" plugin. No data migration — reads attribute terms in place.
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
 * The four levels the owner specified (Make > Model > Submodel > Variant). The live
 * site also carries pa_year_alt and pa_engine_code; they remain available as
 * attributes and can be added to this map without code changes elsewhere.
 */
function ydu_fitment_levels(): array {
	return array(
		'make'     => array( 'taxonomy' => 'pa_make', 'filter' => 'filter_make' ),
		'model'    => array( 'taxonomy' => 'pa_model', 'filter' => 'filter_model' ),
		'submodel' => array( 'taxonomy' => 'pa_submodel', 'filter' => 'filter_submodel' ),
		'variant'  => array( 'taxonomy' => 'pa_variant', 'filter' => 'filter_variant' ),
	);
}

require_once YDU_FITMENT_DIR . 'includes/class-ydu-fitment-cascade.php';
require_once YDU_FITMENT_DIR . 'includes/class-ydu-fitment-rest.php';
require_once YDU_FITMENT_DIR . 'includes/class-ydu-fitment-widget.php';

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
