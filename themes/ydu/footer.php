<?php
/**
 * Site footer. Full footer content lands with task 1.3.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;
?>
</main>

<footer class="site-footer">
	<div class="site-footer__inner">
		<nav class="site-footer__nav" aria-label="<?php esc_attr_e( 'Footer', 'ydu' ); ?>">
			<?php
			wp_nav_menu( array(
				'theme_location' => 'footer',
				'container'      => false,
				'menu_class'     => 'footer-menu',
				'fallback_cb'    => false,
			) );
			?>
		</nav>
		<p class="site-footer__credit">
			&copy; <?php echo esc_html( gmdate( 'Y' ) ); ?> <?php bloginfo( 'name' ); ?> —
			<?php esc_html_e( 'VW, AUDI and VAG Specialists', 'ydu' ); ?>
		</p>
	</div>
</footer>

<?php wp_footer(); ?>
</body>
</html>
