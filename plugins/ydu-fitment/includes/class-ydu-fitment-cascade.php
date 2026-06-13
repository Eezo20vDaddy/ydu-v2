<?php
/**
 * Cascade query layer: derives the Make > Model > Submodel > Variant hierarchy
 * from term co-occurrence on products, over the existing flat pa_* attributes.
 * No tree is stored; each level is computed from products carrying all selected
 * ancestor terms. Results are transient-cached and invalidated on product saves.
 *
 * @package ydu-fitment
 */

defined( 'ABSPATH' ) || exit;

class YDU_Fitment_Cascade {

	const CACHE_TTL = DAY_IN_SECONDS;
	const VER_OPTION = 'ydu_fitment_cache_ver';

	/**
	 * Terms available at $level, given selected ancestor slugs.
	 *
	 * @param string                $level   One of the keys from ydu_fitment_levels().
	 * @param array<string,string>  $parents Map of ancestor level => term slug.
	 * @return array<int,array{id:int,name:string,slug:string}>
	 */
	public function get_terms_for_level( string $level, array $parents = array() ): array {
		$levels = ydu_fitment_levels();
		if ( ! isset( $levels[ $level ] ) ) {
			return array();
		}

		$ancestors = $this->ancestor_chain( $level );
		$parents    = $this->sanitize_parents( $parents, $ancestors );

		$cache_key = $this->cache_key( $level, $parents );
		$cached    = get_transient( $cache_key );
		if ( false !== $cached && is_array( $cached ) ) {
			return $cached;
		}

		$taxonomy = $levels[ $level ]['taxonomy'];

		if ( empty( $parents ) ) {
			// Top level (Make): every used term in the taxonomy.
			$result = $this->format_terms( $this->all_used_terms( $taxonomy ) );
		} else {
			// Child level: terms attached to products that carry ALL ancestor terms.
			$product_ids = $this->products_matching( $parents );
			$result      = empty( $product_ids )
				? array()
				: $this->format_terms( $this->terms_on_products( $taxonomy, $product_ids ) );
		}

		set_transient( $cache_key, $result, self::CACHE_TTL );
		return $result;
	}

	/** Ancestor level keys that must be supplied for $level, in order. */
	private function ancestor_chain( string $level ): array {
		$order = array_keys( ydu_fitment_levels() );
		$idx   = array_search( $level, $order, true );
		return false === $idx ? array() : array_slice( $order, 0, $idx );
	}

	/**
	 * Keep only known ancestor slugs, sanitized, in canonical order.
	 *
	 * @return array<string,string>
	 */
	private function sanitize_parents( array $parents, array $ancestors ): array {
		$clean = array();
		foreach ( $ancestors as $key ) {
			if ( ! empty( $parents[ $key ] ) ) {
				$clean[ $key ] = sanitize_title( (string) $parents[ $key ] );
			}
		}
		return $clean;
	}

	/** All non-empty terms in a product attribute taxonomy. */
	private function all_used_terms( string $taxonomy ): array {
		if ( ! taxonomy_exists( $taxonomy ) ) {
			return array();
		}
		$terms = get_terms( array(
			'taxonomy'   => $taxonomy,
			'hide_empty' => true,
			'orderby'    => 'name',
		) );
		return is_wp_error( $terms ) ? array() : $terms;
	}

	/**
	 * Product IDs (published) carrying every supplied ancestor term.
	 *
	 * @param array<string,string> $parents level => slug
	 * @return int[]
	 */
	private function products_matching( array $parents ): array {
		$levels    = ydu_fitment_levels();
		$tax_query = array( 'relation' => 'AND' );
		foreach ( $parents as $key => $slug ) {
			if ( ! isset( $levels[ $key ] ) ) {
				continue;
			}
			$tax_query[] = array(
				'taxonomy' => $levels[ $key ]['taxonomy'],
				'field'    => 'slug',
				'terms'    => $slug,
			);
		}

		$query = new WP_Query( array(
			'post_type'              => 'product',
			'post_status'            => 'publish',
			'fields'                 => 'ids',
			'posts_per_page'         => -1,
			'no_found_rows'          => true,
			'update_post_meta_cache' => false,
			'update_post_term_cache' => false,
			'tax_query'              => $tax_query, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query
		) );

		return array_map( 'intval', $query->posts );
	}

	/** Distinct terms of $taxonomy attached to the given products. */
	private function terms_on_products( string $taxonomy, array $product_ids ): array {
		if ( ! taxonomy_exists( $taxonomy ) ) {
			return array();
		}
		$terms = wp_get_object_terms( $product_ids, $taxonomy, array(
			'orderby' => 'name',
		) );
		return is_wp_error( $terms ) ? array() : $terms;
	}

	/**
	 * @param WP_Term[] $terms
	 * @return array<int,array{id:int,name:string,slug:string}>
	 */
	private function format_terms( array $terms ): array {
		$out = array();
		foreach ( $terms as $term ) {
			$out[] = array(
				'id'   => (int) $term->term_id,
				'name' => $term->name,
				'slug' => $term->slug,
			);
		}
		return $out;
	}

	private function cache_key( string $level, array $parents ): string {
		ksort( $parents );
		$version = (int) get_option( self::VER_OPTION, 1 );
		return 'ydu_fit_' . $version . '_' . md5( $level . '|' . wp_json_encode( $parents ) );
	}

	/**
	 * Invalidate all cached cascade results by bumping the cache-key version.
	 * Old transients are abandoned and expire via TTL. This is cache-correct
	 * (no stale options-cache reads) and uses no direct SQL.
	 */
	public static function flush_cache(): void {
		$version = (int) get_option( self::VER_OPTION, 1 );
		update_option( self::VER_OPTION, $version + 1, false );
	}
}

// Invalidate cache when the catalog changes.
add_action( 'save_post_product', array( 'YDU_Fitment_Cascade', 'flush_cache' ) );
add_action( 'woocommerce_update_product', array( 'YDU_Fitment_Cascade', 'flush_cache' ) );
add_action( 'created_term', array( 'YDU_Fitment_Cascade', 'flush_cache' ) );
add_action( 'edited_term', array( 'YDU_Fitment_Cascade', 'flush_cache' ) );
add_action( 'delete_term', array( 'YDU_Fitment_Cascade', 'flush_cache' ) );
