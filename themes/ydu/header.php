<?php
/**
 * Site header. The full Variant C shell (utility topbar, search, vehicle
 * selector bar) is built in task 1.3 — this is the structural skeleton.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;
?>
<!doctype html>
<html <?php language_attributes(); ?>>
<head>
	<meta charset="<?php bloginfo( 'charset' ); ?>">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<a class="skip-link screen-reader-text" href="#main"><?php esc_html_e( 'Skip to content', 'ydu' ); ?></a>

<header class="site-header" id="masthead">
	<div class="site-header__inner">
		<div class="site-header__branding">
			<?php
			if ( has_custom_logo() ) {
				the_custom_logo();
			} else {
				?>
				<a class="site-header__title" href="<?php echo esc_url( home_url( '/' ) ); ?>">
					<?php bloginfo( 'name' ); ?>
				</a>
				<?php
			}
			?>
		</div>

		<nav class="site-header__nav" aria-label="<?php esc_attr_e( 'Primary', 'ydu' ); ?>">
			<?php
			wp_nav_menu( array(
				'theme_location' => 'primary',
				'container'      => false,
				'menu_class'     => 'primary-menu',
				'fallback_cb'    => false,
			) );
			?>
		</nav>
	</div>
</header>

<main id="main" class="site-main">
