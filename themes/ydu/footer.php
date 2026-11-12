<?php
/**
 * Site footer — Variant C: brand block, link columns, payment badges.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;
?>
</main>

<footer class="site-footer" id="colophon">
	<div class="container footer-grid">
		<div class="footer-brand">
			<?php echo ydu_logo( 44 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
			<p>
				<?php esc_html_e( 'VW, AUDI and VAG parts specialists. Genuine & OEM parts with manufacturer warranty, dispatched fast from our Forrestdale WA warehouse.', 'ydu' ); ?>
			</p>
			<p style="margin-top:14px">
				<a href="tel:0409853662">0409 853 662</a><br>
				<a href="mailto:info@ydu.com.au">info@ydu.com.au</a><br>
				Unit 4/11 Weedon Road, Forrestdale WA 6112
			</p>
		</div>

		<div>
			<h3><?php esc_html_e( 'Shop', 'ydu' ); ?></h3>
			<ul class="footer-links">
				<li><a href="<?php echo esc_url( get_permalink( wc_get_page_id( 'shop' ) ) ); ?>"><?php esc_html_e( 'All Products', 'ydu' ); ?></a></li>
				<li><a href="<?php echo esc_url( wc_get_cart_url() ); ?>"><?php esc_html_e( 'Cart', 'ydu' ); ?></a></li>
				<li><a href="<?php echo esc_url( wc_get_checkout_url() ); ?>"><?php esc_html_e( 'Checkout', 'ydu' ); ?></a></li>
				<li><a href="<?php echo esc_url( wc_get_page_permalink( 'myaccount' ) ); ?>"><?php esc_html_e( 'My Account', 'ydu' ); ?></a></li>
			</ul>
		</div>

		<div>
			<h3><?php esc_html_e( 'Help', 'ydu' ); ?></h3>
			<ul class="footer-links">
				<?php
				if ( has_nav_menu( 'footer' ) ) {
					wp_nav_menu( array(
						'theme_location' => 'footer',
						'container'      => false,
						'items_wrap'     => '%3$s',
						'fallback_cb'    => false,
						'depth'          => 1,
					) );
				} else {
					?>
					<li><a href="<?php echo esc_url( home_url( '/contact/' ) ); ?>"><?php esc_html_e( 'Contact', 'ydu' ); ?></a></li>
					<li><a href="<?php echo esc_url( home_url( '/find-us/' ) ); ?>"><?php esc_html_e( 'Find Us', 'ydu' ); ?></a></li>
					<li><a href="<?php echo esc_url( wc_get_endpoint_url( 'orders', '', wc_get_page_permalink( 'myaccount' ) ) ); ?>"><?php esc_html_e( 'Check Your Order', 'ydu' ); ?></a></li>
					<li><a href="<?php echo esc_url( home_url( '/refund_returns/' ) ); ?>"><?php esc_html_e( 'Returns & Refunds', 'ydu' ); ?></a></li>
					<?php
				}
				?>
			</ul>
		</div>

		<div>
			<h3><?php esc_html_e( 'Secure Payments', 'ydu' ); ?></h3>
			<div class="pay-badges">
				<span class="pay-badge">Visa</span>
				<span class="pay-badge">Mastercard</span>
				<span class="pay-badge">Amex</span>
				<span class="pay-badge">Apple Pay</span>
				<span class="pay-badge">Google Pay</span>
				<span class="pay-badge">PayPal</span>
			</div>
			<p style="margin-top:18px;font-size:12.5px">
				<span class="stars" aria-hidden="true">★★★★★</span>
				<strong style="color:#fff"><?php esc_html_e( 'Google 4.8', 'ydu' ); ?></strong>
				<?php esc_html_e( 'rated by VAG owners & workshops', 'ydu' ); ?>
			</p>
		</div>
	</div>
	<div class="container footer-bottom">
		<span>&copy; <?php echo esc_html( gmdate( 'Y' ) ); ?> <?php esc_html_e( 'YDU PARTS. All rights reserved.', 'ydu' ); ?></span>
		<span><?php esc_html_e( 'ABN 00 000 000 000', 'ydu' ); ?></span>
	</div>
</footer>

<dialog class="ydu-quick" id="yduQuickView" aria-labelledby="yduQuickTitle">
	<button type="button" class="ydu-quick__close" data-ydu-quick-close aria-label="<?php esc_attr_e( 'Close', 'ydu' ); ?>">
		<?php echo ydu_icon( 'close', 18 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
	</button>
	<div class="ydu-quick__body" data-ydu-quick-body></div>
</dialog>

<?php wp_footer(); ?>
</body>
</html>
