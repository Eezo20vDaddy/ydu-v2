<?php
/**
 * Fallback template.
 *
 * @package ydu
 */

defined( 'ABSPATH' ) || exit;

get_header();

if ( have_posts() ) {
	while ( have_posts() ) {
		the_post();
		?>
		<article id="post-<?php the_ID(); ?>" <?php post_class(); ?>>
			<h1 class="entry-title"><?php the_title(); ?></h1>
			<div class="entry-content"><?php the_content(); ?></div>
		</article>
		<?php
	}
} else {
	?>
	<p><?php esc_html_e( 'Nothing found.', 'ydu' ); ?></p>
	<?php
}

get_footer();
