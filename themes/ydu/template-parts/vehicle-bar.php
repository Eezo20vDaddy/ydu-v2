<?php
/**
 * Vehicle selector bar — static shell (Variant C).
 *
 * Markup and styling are owned by the theme; the cascade behaviour, option
 * data, persistence and redirect are powered by the ydu-fitment plugin, which
 * targets the data-ydu-* hooks below. Until that plugin is active the bar is
 * visible but inert (selects disabled), which is the correct degraded state.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

// Derive the levels from the fitment plugin when active so the bar stays in sync
// with the cascade; otherwise fall back to the agreed 6-level order.
if ( function_exists( 'ydu_fitment_levels' ) ) {
	$ydu_levels = array();
	foreach ( ydu_fitment_levels() as $ydu_key => $ydu_def ) {
		$ydu_levels[ $ydu_key ] = $ydu_def['label'] ?? ucwords( str_replace( '_', ' ', $ydu_key ) );
	}
} else {
	$ydu_levels = array(
		'year'        => __( 'Year', 'ydu' ),
		'make'        => __( 'Make', 'ydu' ),
		'model'       => __( 'Model', 'ydu' ),
		'submodel'    => __( 'Submodel', 'ydu' ),
		'variant'     => __( 'Variant', 'ydu' ),
		'engine_code' => __( 'Engine Code', 'ydu' ),
	);
}
?>
<section class="vehicle-bar on-dark" aria-label="<?php esc_attr_e( 'Vehicle finder', 'ydu' ); ?>" data-ydu-fitment>
	<div class="container vehicle-bar-inner">
		<span class="vb-label">
			<?php echo ydu_icon( 'car', 16 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
			<?php esc_html_e( 'Find parts for:', 'ydu' ); ?>
		</span>
		<form class="vb-form" data-ydu-fitment-form>
			<?php
			foreach ( $ydu_levels as $ydu_key => $ydu_label ) :
				?>
				<label class="visually-hidden" for="ydu-sel-<?php echo esc_attr( $ydu_key ); ?>"><?php echo esc_html( $ydu_label ); ?></label>
				<select class="vb-select" id="ydu-sel-<?php echo esc_attr( $ydu_key ); ?>" data-ydu-level="<?php echo esc_attr( $ydu_key ); ?>">
					<option value=""><?php echo esc_html( $ydu_label ); ?></option>
				</select>
				<?php
			endforeach;
			?>
			<div class="vb-actions">
				<button class="btn-find" type="submit" data-ydu-find disabled>
					<?php echo ydu_icon( 'search', 15 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
					<?php esc_html_e( 'Find Parts', 'ydu' ); ?>
				</button>
				<button class="btn-reset" type="reset" data-ydu-reset><?php esc_html_e( 'Reset', 'ydu' ); ?></button>
			</div>
		</form>
		<span class="my-vehicle-chip" data-ydu-chip aria-live="polite">
			<span class="chip-dot" aria-hidden="true"></span>
			<?php esc_html_e( 'My Vehicle:', 'ydu' ); ?>&nbsp;<strong data-ydu-chip-text>—</strong>
		</span>
	</div>
</section>
