<?php
/**
 * YDU theme bootstrap.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

define( 'YDU_VERSION', '0.1.0' );
define( 'YDU_DIR', get_template_directory() );
define( 'YDU_URI', get_template_directory_uri() );

require YDU_DIR . '/inc/setup.php';
require YDU_DIR . '/inc/assets.php';
require YDU_DIR . '/inc/woocommerce.php';
