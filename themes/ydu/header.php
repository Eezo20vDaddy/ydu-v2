<?php
/**
 * Site header — Variant C: utility topbar, logo + combined search + nav + icons,
 * mobile drawer. The vehicle selector bar is rendered after the header via the
 * `ydu_after_header` hook (the ydu-fitment plugin powers it; the theme provides
 * a static fallback in template-parts/vehicle-bar.php).
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

$ydu_wishlist = ydu_wishlist_count();
$ydu_compare  = ydu_compare_count();
$ydu_cart     = ydu_cart_count();
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

<a class="skip-link" href="#main"><?php esc_html_e( 'Skip to content', 'ydu' ); ?></a>

<div class="topbar">
	<div class="container topbar-inner">
		<a href="tel:0409853662" aria-label="<?php esc_attr_e( 'Call YDU Parts on 0409 853 662', 'ydu' ); ?>">
			<?php echo ydu_icon( 'phone', 13 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
			0409 853 662
		</a>
		<span class="topbar-mid">
			<?php echo ydu_icon( 'truck', 13 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
			<?php esc_html_e( 'Same-day dispatch before 1pm AWST · Fast nationwide delivery', 'ydu' ); ?>
		</span>
		<span class="topbar-rating">
			<span class="stars" aria-hidden="true">★★★★★</span>
			<strong style="color:#fff"><?php esc_html_e( 'Google 4.8', 'ydu' ); ?></strong>
			<span aria-hidden="true"><?php esc_html_e( 'rated', 'ydu' ); ?></span>
		</span>
	</div>
</div>

<header class="site-header" id="masthead">
	<div class="container header-grid">
		<div class="header-row1">
			<button class="icon-btn hamburger" id="yduHamburger" aria-expanded="false" aria-controls="yduDrawer" aria-label="<?php esc_attr_e( 'Open menu', 'ydu' ); ?>">
				<?php echo ydu_icon( 'menu', 22 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
			</button>
			<a class="logo-link" href="<?php echo esc_url( home_url( '/' ) ); ?>" aria-label="<?php esc_attr_e( 'YDU PARTS home', 'ydu' ); ?>">
				<?php echo ydu_logo( 40 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
			</a>
			<span class="tagline"><?php esc_html_e( 'VW, AUDI and VAG Specialists', 'ydu' ); ?></span>
			<div class="header-icons">
				<a class="icon-btn icon-hide-mobile" href="<?php echo esc_url( wc_get_page_permalink( 'myaccount' ) ); ?>" aria-label="<?php esc_attr_e( 'My account', 'ydu' ); ?>">
					<?php echo ydu_icon( 'user' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
				</a>
				<?php if ( null !== $ydu_wishlist ) : ?>
					<a class="icon-btn icon-hide-mobile" href="<?php echo esc_url( home_url( '/wishlist/' ) ); ?>" aria-label="<?php echo esc_attr( sprintf( /* translators: %d: count */ __( 'Wishlist, %d items', 'ydu' ), $ydu_wishlist ) ); ?>">
						<?php echo ydu_icon( 'heart' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
						<?php if ( $ydu_wishlist > 0 ) : ?><span class="badge" aria-hidden="true"><?php echo esc_html( $ydu_wishlist ); ?></span><?php endif; ?>
					</a>
				<?php endif; ?>
				<?php if ( null !== $ydu_compare ) : ?>
					<a class="icon-btn icon-hide-mobile" href="<?php echo esc_url( home_url( '/compare/' ) ); ?>" aria-label="<?php echo esc_attr( sprintf( /* translators: %d: count */ __( 'Compare, %d items', 'ydu' ), $ydu_compare ) ); ?>">
						<?php echo ydu_icon( 'compare' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
						<?php if ( $ydu_compare > 0 ) : ?><span class="badge" aria-hidden="true"><?php echo esc_html( $ydu_compare ); ?></span><?php endif; ?>
					</a>
				<?php endif; ?>
				<a class="icon-btn" href="<?php echo esc_url( wc_get_cart_url() ); ?>" aria-label="<?php echo esc_attr( sprintf( /* translators: %d: count */ __( 'Cart, %d items', 'ydu' ), $ydu_cart ) ); ?>">
					<?php echo ydu_icon( 'cart' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
					<?php if ( $ydu_cart > 0 ) : ?><span class="badge" id="yduCartCount" aria-hidden="true"><?php echo esc_html( $ydu_cart ); ?></span><?php endif; ?>
				</a>
			</div>
		</div>

		<form class="search-row" role="search" method="get" action="<?php echo esc_url( home_url( '/' ) ); ?>" aria-label="<?php esc_attr_e( 'Product search', 'ydu' ); ?>">
			<input type="hidden" name="post_type" value="product">
			<div class="search-combo">
				<label class="visually-hidden" for="yduSearchCat"><?php esc_html_e( 'Search in category', 'ydu' ); ?></label>
				<select class="search-cat" id="yduSearchCat" name="product_cat">
					<option value=""><?php esc_html_e( 'All Categories', 'ydu' ); ?></option>
					<?php foreach ( ydu_search_categories() as $ydu_cat ) : ?>
						<option value="<?php echo esc_attr( $ydu_cat->slug ); ?>"><?php echo esc_html( $ydu_cat->name ); ?></option>
					<?php endforeach; ?>
				</select>
				<label class="visually-hidden" for="yduSearchInput"><?php esc_html_e( 'Search by part number or keyword', 'ydu' ); ?></label>
				<input class="search-input" id="yduSearchInput" type="search" name="s" value="<?php echo esc_attr( get_search_query() ); ?>" autocomplete="off"
					placeholder="<?php esc_attr_e( 'Search part number or keyword… e.g. 06L145612L, wastegate', 'ydu' ); ?>">
				<button class="search-btn" type="submit">
					<?php echo ydu_icon( 'search', 17 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
					<span><?php esc_html_e( 'Search', 'ydu' ); ?></span>
				</button>
			</div>
		</form>

		<nav class="main-nav" aria-label="<?php esc_attr_e( 'Main', 'ydu' ); ?>">
			<?php
			if ( has_nav_menu( 'primary' ) ) {
				wp_nav_menu( array(
					'theme_location' => 'primary',
					'container'      => false,
					'menu_class'     => '',
					'fallback_cb'    => false,
					'depth'          => 1,
				) );
			} else {
				?>
				<ul>
					<li><a href="<?php echo esc_url( get_permalink( wc_get_page_id( 'shop' ) ) ); ?>"><?php esc_html_e( 'Shop', 'ydu' ); ?></a></li>
					<li><a href="<?php echo esc_url( home_url( '/contact/' ) ); ?>"><?php esc_html_e( 'Contact', 'ydu' ); ?></a></li>
					<li><a href="<?php echo esc_url( wc_get_endpoint_url( 'orders', '', wc_get_page_permalink( 'myaccount' ) ) ); ?>"><?php esc_html_e( 'Check Your Order', 'ydu' ); ?></a></li>
					<li><a href="<?php echo esc_url( home_url( '/find-us/' ) ); ?>"><?php esc_html_e( 'Find Us', 'ydu' ); ?></a></li>
				</ul>
				<?php
			}
			?>
		</nav>
	</div>
</header>

<div class="drawer-backdrop" id="yduDrawerBackdrop" hidden></div>
<div class="mobile-drawer" id="yduDrawer" role="dialog" aria-modal="true" aria-label="<?php esc_attr_e( 'Menu', 'ydu' ); ?>" hidden>
	<div class="drawer-head">
		<?php echo ydu_logo( 36 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
		<button class="icon-btn" id="yduDrawerClose" aria-label="<?php esc_attr_e( 'Close menu', 'ydu' ); ?>">
			<?php echo ydu_icon( 'close', 20 ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
		</button>
	</div>
	<nav aria-label="<?php esc_attr_e( 'Mobile', 'ydu' ); ?>">
		<?php
		if ( has_nav_menu( 'primary' ) ) {
			wp_nav_menu( array(
				'theme_location' => 'primary',
				'container'      => false,
				'items_wrap'     => '%3$s',
				'fallback_cb'    => false,
				'depth'          => 1,
			) );
		} else {
			?>
			<a href="<?php echo esc_url( get_permalink( wc_get_page_id( 'shop' ) ) ); ?>"><?php esc_html_e( 'Shop', 'ydu' ); ?></a>
			<a href="<?php echo esc_url( home_url( '/contact/' ) ); ?>"><?php esc_html_e( 'Contact', 'ydu' ); ?></a>
			<a href="<?php echo esc_url( home_url( '/find-us/' ) ); ?>"><?php esc_html_e( 'Find Us', 'ydu' ); ?></a>
			<?php
		}
		?>
		<a href="<?php echo esc_url( wc_get_page_permalink( 'myaccount' ) ); ?>"><?php esc_html_e( 'My Account', 'ydu' ); ?></a>
	</nav>
	<div class="drawer-foot">
		<a href="tel:0409853662">0409 853 662</a>
		Unit 4/11 Weedon Road, Forrestdale WA 6112<br>
		<span class="stars" aria-hidden="true">★★★★★</span> <?php esc_html_e( 'Google 4.8 rated', 'ydu' ); ?>
	</div>
</div>

<?php
/**
 * Vehicle selector bar. The ydu-fitment plugin hooks here at priority 10;
 * if it's inactive, the theme renders the static shell as a fallback.
 */
if ( ! has_action( 'ydu_after_header' ) ) {
	get_template_part( 'template-parts/vehicle-bar' );
}
do_action( 'ydu_after_header' );
?>

<main id="main" class="site-main">
