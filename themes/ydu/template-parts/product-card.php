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

$ydu_permalink = get_permalink( $product->get_id() );
$ydu_cat_name  = ydu_product_card_category_label( $product->get_id() );

$ydu_image_ids = array();
$thumb_id      = $product->get_image_id();
if ( $thumb_id ) {
	$ydu_image_ids[] = (int) $thumb_id;
}
foreach ( $product->get_gallery_image_ids() as $gallery_id ) {
	$gallery_id = (int) $gallery_id;
	if ( $gallery_id && ! in_array( $gallery_id, $ydu_image_ids, true ) ) {
		$ydu_image_ids[] = $gallery_id;
	}
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
			<?php if ( empty( $ydu_image_ids ) ) : ?>
				<div class="pc-placeholder" role="img" aria-label="<?php esc_attr_e( 'Image coming soon', 'ydu' ); ?>">
					<?php echo ydu_icon( 'image', 34 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
					<span><?php esc_html_e( 'Image coming soon', 'ydu' ); ?></span>
				</div>
			<?php else : ?>
				<div class="pc-gallery" data-pc-interval="5000">
					<?php
					foreach ( $ydu_image_ids as $ydu_index => $ydu_attachment_id ) {
						$ydu_slide_class = 'pc-gallery__slide';
						if ( 0 === $ydu_index ) {
							$ydu_slide_class .= ' is-active';
						}
						echo wp_get_attachment_image(
							$ydu_attachment_id,
							'woocommerce_thumbnail',
							false,
							array(
								'loading' => 0 === $ydu_index ? 'lazy' : 'lazy',
								'alt'     => esc_attr( $product->get_name() ),
								'class'   => $ydu_slide_class,
							)
						);
					}
					?>
				</div>
			<?php endif; ?>
		</a>
	</div>
	<div class="pc-body">
		<div class="pc-topline">
			<?php if ( $ydu_cat_name ) : ?>
				<span class="part-no"><?php echo esc_html( $ydu_cat_name ); ?></span>
			<?php endif; ?>
			<span class="stock-badge <?php echo esc_attr( $ydu_badge_class ); ?>"><?php echo esc_html( $ydu_badge_text ); ?></span>
		</div>
		<a class="pc-name-link" href="<?php echo esc_url( $ydu_permalink ); ?>">
			<h3 class="pc-name"><?php echo esc_html( $product->get_name() ); ?></h3>
		</a>
		<?php if ( $ydu_cat_name ) : ?>
			<span class="pc-chip"><?php echo esc_html( $ydu_cat_name ); ?></span>
		<?php endif; ?>
		<?php ydu_list_actions( $product, 'card' ); ?>
		<div class="pc-foot">
			<span class="pc-price"><?php echo wp_kses_post( $product->get_price_html() ); ?></span>
			<?php
			woocommerce_template_loop_add_to_cart( array( 'class' => 'btn-cart' ) );
			?>
		</div>
	</div>
</li>
