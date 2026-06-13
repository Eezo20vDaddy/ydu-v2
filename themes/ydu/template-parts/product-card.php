<?php
/**
 * Product card (Variant C) — renders the current global $product. Used by the
 * home featured grid and the shop/category archives (via content-product.php).
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

global $product;
if ( ! $product instanceof WC_Product ) {
	return;
}

$ydu_sku       = $product->get_sku();
$ydu_permalink = get_permalink( $product->get_id() );
$ydu_cats      = wc_get_product_category_list( $product->get_id() );
$ydu_cat_name  = '';
$ydu_terms     = get_the_terms( $product->get_id(), 'product_cat' );
if ( $ydu_terms && ! is_wp_error( $ydu_terms ) ) {
	$ydu_cat_name = $ydu_terms[0]->name;
}

// Stock badge.
if ( ! $product->is_in_stock() ) {
	$ydu_badge_class = 'stock-ship';
	$ydu_badge_text  = __( 'Backorder', 'ydu' );
} elseif ( $product->is_on_backorder() ) {
	$ydu_badge_class = 'stock-ship';
	$ydu_badge_text  = __( '3–5 Days', 'ydu' );
} else {
	$ydu_badge_class = 'stock-in';
	$ydu_badge_text  = __( 'In Stock', 'ydu' );
}
?>
<li <?php wc_product_class( 'product-card', $product ); ?>>
	<div class="pc-media">
		<a href="<?php echo esc_url( $ydu_permalink ); ?>" tabindex="-1" aria-hidden="true">
			<?php
			if ( has_post_thumbnail( $product->get_id() ) ) {
				echo wp_get_attachment_image(
					get_post_thumbnail_id( $product->get_id() ),
					'woocommerce_thumbnail',
					false,
					array( 'loading' => 'lazy', 'alt' => esc_attr( $product->get_name() ) )
				);
			} else {
				?>
				<div class="pc-placeholder" role="img" aria-label="<?php echo esc_attr( sprintf( /* translators: %s: part number */ __( 'Image coming soon for %s', 'ydu' ), $ydu_sku ?: $product->get_name() ) ); ?>">
					<?php echo ydu_icon( 'image', 34 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
					<span><?php echo esc_html( $ydu_sku ?: 'YDU' ); ?></span>
				</div>
				<?php
			}
			?>
		</a>
	</div>
	<div class="pc-body">
		<div class="pc-topline">
			<?php if ( $ydu_sku ) : ?>
				<span class="part-no"><?php echo esc_html( $ydu_sku ); ?></span>
			<?php else : ?>
				<span class="part-no">YDU</span>
			<?php endif; ?>
			<span class="stock-badge <?php echo esc_attr( $ydu_badge_class ); ?>"><?php echo esc_html( $ydu_badge_text ); ?></span>
		</div>
		<a class="pc-name-link" href="<?php echo esc_url( $ydu_permalink ); ?>">
			<h3 class="pc-name"><?php echo esc_html( $product->get_name() ); ?></h3>
		</a>
		<?php if ( $ydu_cat_name ) : ?>
			<span class="pc-chip"><?php echo esc_html( $ydu_cat_name ); ?></span>
		<?php endif; ?>
		<div class="pc-foot">
			<span class="pc-price"><?php echo wp_kses_post( $product->get_price_html() ); ?></span>
			<?php
			woocommerce_template_loop_add_to_cart( array( 'class' => 'btn-cart' ) );
			?>
		</div>
	</div>
</li>
