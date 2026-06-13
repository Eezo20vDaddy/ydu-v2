<?php
/**
 * Front page (Variant C): hero + trust strip + category grid + featured
 * products + promo banners. The persistent vehicle finder bar renders globally
 * from the header; this hero promotes it and shows trust stats.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

get_header();

$ydu_shop_url = wc_get_page_permalink( 'shop' );
?>

<section class="hero on-dark">
	<div class="container hero-inner">
		<div>
			<span class="hero-kicker">
				<?php echo ydu_icon( 'bolt', 14 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
				<?php esc_html_e( 'VW, AUDI and VAG Specialists', 'ydu' ); ?>
			</span>
			<h1><?php esc_html_e( 'The trade counter for genuine & OEM VAG parts.', 'ydu' ); ?></h1>
			<p class="lede"><?php esc_html_e( 'Know your part number? Search it straight in. Otherwise set your vehicle in the selector above and we’ll filter the whole catalogue to exact-fit parts — genuine and OEM, with manufacturer warranty, shipped fast from Perth WA.', 'ydu' ); ?></p>
			<div class="hero-cta-row">
				<a class="btn-primary" href="<?php echo esc_url( $ydu_shop_url ); ?>">
					<?php esc_html_e( 'Browse Catalogue', 'ydu' ); ?>
					<?php echo ydu_icon( 'arrow', 15 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
				</a>
				<a class="btn-ghost" href="#featured"><?php esc_html_e( 'Featured Parts', 'ydu' ); ?></a>
			</div>
		</div>
		<div class="hero-stats" role="list" aria-label="<?php esc_attr_e( 'Why buy from YDU Parts', 'ydu' ); ?>">
			<div class="hero-stat" role="listitem"><div class="num">4.8★</div><div class="lbl"><?php esc_html_e( 'Google rating', 'ydu' ); ?></div></div>
			<div class="hero-stat" role="listitem"><div class="num"><?php echo esc_html( ydu_catalog_count_label() ); ?></div><div class="lbl"><?php esc_html_e( 'VAG part lines', 'ydu' ); ?></div></div>
			<div class="hero-stat" role="listitem"><div class="num">1pm</div><div class="lbl"><?php esc_html_e( 'Same-day dispatch cut-off', 'ydu' ); ?></div></div>
			<div class="hero-stat" role="listitem"><div class="num"><?php esc_html_e( 'Perth WA', 'ydu' ); ?></div><div class="lbl"><?php esc_html_e( 'Local stock & support', 'ydu' ); ?></div></div>
		</div>
	</div>
</section>

<section class="trust" aria-label="<?php esc_attr_e( 'Why shop with us', 'ydu' ); ?>">
	<div class="container trust-grid">
		<div class="trust-item"><?php echo ydu_category_icon( 'gauge' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?><div><strong><?php esc_html_e( 'Google 4.8★ rated', 'ydu' ); ?></strong><?php esc_html_e( 'Trusted by VAG owners & workshops', 'ydu' ); ?></div></div>
		<div class="trust-item"><?php echo ydu_category_icon( 'truck' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?><div><strong><?php esc_html_e( 'Fast nationwide delivery', 'ydu' ); ?></strong><?php esc_html_e( 'Same-day dispatch before 1pm AWST', 'ydu' ); ?></div></div>
		<div class="trust-item"><?php echo ydu_category_icon( 'disc' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?><div><strong><?php esc_html_e( 'Genuine & OEM parts', 'ydu' ); ?></strong><?php esc_html_e( 'With manufacturer warranty', 'ydu' ); ?></div></div>
		<div class="trust-item"><?php echo ydu_category_icon( 'truck' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?><div><strong><?php esc_html_e( 'Perth WA based', 'ydu' ); ?></strong><?php esc_html_e( 'Forrestdale warehouse & pickup', 'ydu' ); ?></div></div>
	</div>
</section>

<section class="section" id="categories" aria-labelledby="ydu-cat-h">
	<div class="container">
		<div class="section-head">
			<div>
				<h2 id="ydu-cat-h"><?php esc_html_e( 'Shop by Category', 'ydu' ); ?></h2>
				<p class="sub"><?php esc_html_e( 'Every line, catalogued by system — the fast way in when you don’t have a part number.', 'ydu' ); ?></p>
			</div>
			<a class="section-link" href="<?php echo esc_url( $ydu_shop_url ); ?>"><?php esc_html_e( 'All categories →', 'ydu' ); ?></a>
		</div>
		<div class="cat-grid">
			<?php
			$ydu_cats = get_terms( array(
				'taxonomy'   => 'product_cat',
				'hide_empty' => true,
				'parent'     => 0,
				'orderby'    => 'count',
				'order'      => 'DESC',
				'number'     => 11,
			) );
			if ( ! is_wp_error( $ydu_cats ) ) {
				foreach ( $ydu_cats as $ydu_cat ) {
					printf(
						'<a class="cat-tile" href="%1$s">%2$s%3$s</a>',
						esc_url( get_term_link( $ydu_cat ) ),
						ydu_category_icon( ydu_category_icon_name( $ydu_cat->slug, $ydu_cat->name ) ), // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
						esc_html( $ydu_cat->name )
					);
				}
			}
			?>
			<a class="cat-tile" href="<?php echo esc_url( $ydu_shop_url ); ?>" style="color:var(--primary)">
				<?php echo ydu_category_icon( 'grid' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
				<?php esc_html_e( 'View All', 'ydu' ); ?>
			</a>
		</div>
	</div>
</section>

<section class="section" id="featured" aria-labelledby="ydu-feat-h" style="padding-top:0">
	<div class="container">
		<div class="section-head">
			<div>
				<h2 id="ydu-feat-h"><?php esc_html_e( 'Featured Parts', 'ydu' ); ?></h2>
				<p class="sub"><?php esc_html_e( 'Genuine & OEM, priced in AUD inc. GST. Part numbers shown — cross-check yours before ordering.', 'ydu' ); ?></p>
			</div>
			<a class="section-link" href="<?php echo esc_url( $ydu_shop_url ); ?>"><?php esc_html_e( 'Shop all →', 'ydu' ); ?></a>
		</div>
		<?php
		$ydu_featured = wc_get_products( array(
			'status'       => 'publish',
			'limit'        => 8,
			'orderby'      => 'date',
			'order'        => 'DESC',
			'stock_status' => 'instock',
		) );
		if ( $ydu_featured ) {
			echo '<ul class="products product-grid">';
			global $product;
			$ydu_prev = $product;
			foreach ( $ydu_featured as $ydu_p ) {
				$product = $ydu_p; // phpcs:ignore WordPress.WP.GlobalVariablesOverride
				setup_postdata( get_post( $ydu_p->get_id() ) );
				get_template_part( 'template-parts/product-card' );
			}
			$product = $ydu_prev; // phpcs:ignore WordPress.WP.GlobalVariablesOverride
			wp_reset_postdata();
			echo '</ul>';
		}
		?>
	</div>
</section>

<section class="section" aria-label="<?php esc_attr_e( 'Current offers', 'ydu' ); ?>" style="padding-top:0">
	<div class="container">
		<div class="promo-grid">
			<div class="promo promo-battery">
				<span class="promo-eyebrow"><?php esc_html_e( 'Limited time', 'ydu' ); ?></span>
				<h3><span class="pct"><?php esc_html_e( '60% OFF', 'ydu' ); ?></span> <?php esc_html_e( 'Car Batteries', 'ydu' ); ?></h3>
				<p><?php esc_html_e( 'Quality replacement batteries for the VAG range — while stocks last.', 'ydu' ); ?></p>
				<div><a class="btn-primary" href="<?php echo esc_url( $ydu_shop_url ); ?>"><?php esc_html_e( 'Shop batteries', 'ydu' ); ?></a></div>
			</div>
			<div class="promo promo-welcome">
				<span class="promo-eyebrow" style="color:var(--primary)"><?php esc_html_e( 'New customers', 'ydu' ); ?></span>
				<h3><?php esc_html_e( '5% off your first order', 'ydu' ); ?></h3>
				<p><?php esc_html_e( 'Use this code at checkout for 5% off storewide.', 'ydu' ); ?></p>
				<div class="code-row">
					<span class="code-chip">WELCOME5</span>
					<button class="btn-copy" type="button" data-ydu-copy="WELCOME5"><?php esc_html_e( 'Copy code', 'ydu' ); ?></button>
				</div>
			</div>
		</div>
	</div>
</section>

<?php
get_footer();
