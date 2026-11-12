<?php
/**
 * Finder widget wiring: enqueues the Interactivity-API finder module on the
 * front end and exposes a [ydu_finder] shortcode + render function so the
 * finder survives a theme swap. The persistent header bar markup lives in the
 * active theme (template-parts/vehicle-bar.php); this module powers any element
 * carrying the data-ydu-fitment-form hook.
 *
 * @package ydu-fitment
 */

defined( 'ABSPATH' ) || exit;

class YDU_Fitment_Widget {

	public static function init(): void {
		add_action( 'wp_enqueue_scripts', array( __CLASS__, 'enqueue' ) );
		add_shortcode( 'ydu_finder', array( __CLASS__, 'shortcode' ) );
	}

	public static function enqueue(): void {
		$asset_file = YDU_FITMENT_DIR . 'build/finder.asset.php';
		if ( ! file_exists( $asset_file ) ) {
			return;
		}
		$asset = require $asset_file;

		wp_enqueue_script(
			'ydu-fitment-finder',
			YDU_FITMENT_URL . 'build/finder.js',
			$asset['dependencies'],
			$asset['version'],
			array( 'in_footer' => true, 'strategy' => 'defer' )
		);

		// Config consumed by the script (REST root + shop URL for the redirect).
		wp_add_inline_script(
			'ydu-fitment-finder',
			'window.yduFitmentConfig = ' . wp_json_encode( self::store_config() ) . ';',
			'before'
		);
	}

	/**
	 * Initial Interactivity store state, printed once for the module to hydrate.
	 */
	public static function store_config(): array {
		return array(
			'restUrl' => esc_url_raw( rest_url( YDU_Fitment_REST::NAMESPACE ) ),
			'shopUrl' => wc_get_page_permalink( 'shop' ),
			'levels'   => array_keys( ydu_fitment_levels() ),
			'labels'   => array_map(
				static fn( $l ) => $l['label'],
				ydu_fitment_levels()
			),
			'cacheVer' => (int) get_option( YDU_Fitment_Cascade::VER_OPTION, 1 ),
			'filters' => array_map(
				static fn( $l ) => $l['filter'],
				ydu_fitment_levels()
			),
		);
	}

	public static function shortcode( $atts ): string {
		// Reuse the theme's bar markup if present, else a minimal self-contained form.
		$template = locate_template( 'template-parts/vehicle-bar.php' );
		ob_start();
		if ( $template ) {
			load_template( $template, false );
		} else {
			self::fallback_markup();
		}
		return (string) ob_get_clean();
	}

	private static function fallback_markup(): void {
		$levels = ydu_fitment_levels();
		echo '<form class="ydu-finder" data-ydu-fitment-form>';
		foreach ( $levels as $key => $config ) {
			printf(
				'<select data-ydu-level="%1$s"><option value="">%2$s</option></select>',
				esc_attr( $key ),
				esc_html( $config['label'] )
			);
		}
		echo '<button type="submit" data-ydu-find disabled>' . esc_html__( 'Find Parts', 'ydu-fitment' ) . '</button>';
		echo '<button type="reset" data-ydu-reset>' . esc_html__( 'Reset', 'ydu-fitment' ) . '</button>';
		echo '</form>';
	}
}
