<?php
/**
 * Front-end asset registration.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

add_action( 'wp_enqueue_scripts', 'ydu_enqueue_assets' );

function ydu_enqueue_assets(): void {
	$asset_file = YDU_DIR . '/build/index.asset.php';
	$asset      = file_exists( $asset_file )
		? require $asset_file
		: array(
			'dependencies' => array(),
			'version'      => YDU_VERSION,
		);

	wp_enqueue_style(
		'ydu-fonts',
		'https://api.fontshare.com/v2/css?f[]=clash-grotesk@400,500,600,700&display=swap',
		array(),
		YDU_VERSION
	);

	if ( file_exists( YDU_DIR . '/build/style-index.css' ) ) {
		wp_enqueue_style(
			'ydu-style',
			YDU_URI . '/build/style-index.css',
			array( 'ydu-fonts' ),
			$asset['version']
		);
	}

	if ( file_exists( YDU_DIR . '/build/index.js' ) ) {
		wp_enqueue_script(
			'ydu-frontend',
			YDU_URI . '/build/index.js',
			$asset['dependencies'],
			$asset['version'],
			array( 'in_footer' => true )
		);
	}
}
