<?php
/**
 * Shared fixture: registers the product post type + pa_* fitment taxonomies and
 * seeds a small known catalogue so cascade behaviour is deterministic.
 *
 * Base catalogue (clean, unambiguous):
 *   P1: VW  / Golf Mk5 / Hatch     / GTI
 *   P2: VW  / Golf Mk5 / Hatch     / 2.0 FSI
 *   P3: VW  / Golf Mk6 / Hatch     / R
 *   P4: Audi/ A3 8P    / Sportback / 2.0 TFSI
 *   P5: Audi/ A3 8P    / Sportback / 1.8 TFSI
 *
 * A multi-fit part (added on demand by add_multifit_part()) exercises the
 * documented flat-model co-occurrence quirk in its own dedicated test.
 *
 * @package ydu-fitment
 */

abstract class YDU_Fitment_TestCase extends WP_UnitTestCase {

	protected function setUp(): void {
		parent::setUp();

		if ( ! post_type_exists( 'product' ) ) {
			register_post_type( 'product', array( 'public' => true, 'label' => 'Product' ) );
		}
		foreach ( ydu_fitment_levels() as $level ) {
			if ( ! taxonomy_exists( $level['taxonomy'] ) ) {
				register_taxonomy( $level['taxonomy'], 'product', array( 'hierarchical' => false, 'public' => false ) );
			}
		}

		$this->seed_catalogue();
		YDU_Fitment_Cascade::flush_cache();
	}

	protected function make_product( array $fitment ): int {
		$id = self::factory()->post->create( array( 'post_type' => 'product', 'post_status' => 'publish' ) );
		foreach ( $fitment as $taxonomy => $term_name ) {
			wp_set_object_terms( $id, $term_name, $taxonomy );
		}
		return $id;
	}

	private function seed_catalogue(): void {
		$this->make_product( array( 'pa_make' => 'Volkswagen', 'pa_model' => 'Golf Mk5', 'pa_submodel' => 'Hatch', 'pa_variant' => 'GTI' ) );
		$this->make_product( array( 'pa_make' => 'Volkswagen', 'pa_model' => 'Golf Mk5', 'pa_submodel' => 'Hatch', 'pa_variant' => '2.0 FSI' ) );
		$this->make_product( array( 'pa_make' => 'Volkswagen', 'pa_model' => 'Golf Mk6', 'pa_submodel' => 'Hatch', 'pa_variant' => 'R' ) );
		$this->make_product( array( 'pa_make' => 'Audi', 'pa_model' => 'A3 8P', 'pa_submodel' => 'Sportback', 'pa_variant' => '2.0 TFSI' ) );
		$this->make_product( array( 'pa_make' => 'Audi', 'pa_model' => 'A3 8P', 'pa_submodel' => 'Sportback', 'pa_variant' => '1.8 TFSI' ) );
	}

	/** Adds one part tagged for both a VW Golf Mk5 GTI and an Audi A3 8P 2.0 TFSI. */
	protected function add_multifit_part(): int {
		$id = $this->make_product( array(
			'pa_make'     => array( 'Volkswagen', 'Audi' ),
			'pa_model'    => array( 'Golf Mk5', 'A3 8P' ),
			'pa_submodel' => array( 'Hatch', 'Sportback' ),
			'pa_variant'  => array( 'GTI', '2.0 TFSI' ),
		) );
		YDU_Fitment_Cascade::flush_cache();
		return $id;
	}

	/** @return string[] sorted slugs from a cascade/REST result */
	protected function slugs( array $terms ): array {
		$slugs = array_map( static fn( $t ) => is_array( $t ) ? $t['slug'] : $t->slug, $terms );
		sort( $slugs );
		return $slugs;
	}
}
