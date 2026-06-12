<?php
/**
 * Theme supports, menus, and image sizes.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

add_action( 'after_setup_theme', 'ydu_setup' );

function ydu_setup(): void {
	load_theme_textdomain( 'ydu', YDU_DIR . '/languages' );

	add_theme_support( 'title-tag' );
	add_theme_support( 'post-thumbnails' );
	add_theme_support( 'custom-logo', array(
		'height'      => 56,
		'width'       => 170,
		'flex-height' => true,
		'flex-width'  => true,
	) );
	add_theme_support( 'html5', array(
		'search-form',
		'gallery',
		'caption',
		'style',
		'script',
		'navigation-widgets',
	) );
	add_theme_support( 'responsive-embeds' );

	add_theme_support( 'woocommerce' );
	add_theme_support( 'wc-product-gallery-zoom' );
	add_theme_support( 'wc-product-gallery-lightbox' );
	add_theme_support( 'wc-product-gallery-slider' );

	register_nav_menus( array(
		'primary' => __( 'Primary Menu', 'ydu' ),
		'footer'  => __( 'Footer Menu', 'ydu' ),
	) );
}
