<?php
/**
 * Cascade query-layer tests (task 3.1, tdd:required).
 *
 * @package ydu-fitment
 */

require_once __DIR__ . '/class-ydu-fitment-testcase.php';

class YDU_Fitment_Cascade_Test extends YDU_Fitment_TestCase {

	private YDU_Fitment_Cascade $cascade;

	protected function setUp(): void {
		parent::setUp();
		$this->cascade = new YDU_Fitment_Cascade();
	}

	public function test_makes_returns_all_used_makes(): void {
		$makes = $this->cascade->get_terms_for_level( 'make' );
		$this->assertSame( array( 'audi', 'volkswagen' ), $this->slugs( $makes ) );
	}

	public function test_models_filtered_by_make(): void {
		$vw = $this->cascade->get_terms_for_level( 'model', array( 'make' => 'volkswagen' ) );
		$this->assertSame( array( 'golf-mk5', 'golf-mk6' ), $this->slugs( $vw ) );

		$audi = $this->cascade->get_terms_for_level( 'model', array( 'make' => 'audi' ) );
		$this->assertSame( array( 'a3-8p' ), $this->slugs( $audi ) );
	}

	public function test_submodels_filtered_by_make_and_model(): void {
		$subs = $this->cascade->get_terms_for_level( 'submodel', array( 'make' => 'volkswagen', 'model' => 'golf-mk5' ) );
		$this->assertSame( array( 'hatch' ), $this->slugs( $subs ) );
	}

	public function test_variants_filtered_to_exact_chain(): void {
		$variants = $this->cascade->get_terms_for_level( 'variant', array(
			'make'     => 'volkswagen',
			'model'    => 'golf-mk5',
			'submodel' => 'hatch',
		) );
		// WordPress slugifies "2.0 FSI" → "2-0-fsi".
		$this->assertSame( array( '2-0-fsi', 'gti' ), $this->slugs( $variants ) );
	}

	public function test_multifit_part_splits_by_make_for_cascade(): void {
		$this->add_multifit_part();
		$vw_models = $this->cascade->get_terms_for_level( 'model', array( 'make' => 'volkswagen' ) );
		$this->assertContains( 'golf-mk5', $this->slugs( $vw_models ) );
		$this->assertNotContains( 'a3-8p', $this->slugs( $vw_models ) );
	}

	/**
	 * Wide SKUs store a union of makes and models. A3 is owned by the single-make
	 * Audi product, so Year 2003 + Cupra does not list it. Formentor appears only
	 * on the multi-make product, so neither Cupra nor Audi lists it.
	 */
	public function test_cupra_excludes_models_owned_by_audi(): void {
		$this->make_product( array(
			'pa_make'  => 'Audi',
			'pa_model' => 'A3',
		) );
		$this->make_product( array(
			'pa_make'     => array( 'Audi', 'Cupra' ),
			'pa_model'    => array( 'A3', 'Formentor' ),
			'pa_year_alt' => '2003',
		) );
		YDU_Fitment_Cascade::flush_cache();

		$cupra = $this->cascade->get_terms_for_level( 'model', array(
			'year' => '2003',
			'make' => 'cupra',
		) );
		$this->assertSame( array(), $this->slugs( $cupra ) );

		$audi = $this->cascade->get_terms_for_level( 'model', array( 'make' => 'audi' ) );
		$this->assertContains( 'a3', $this->slugs( $audi ) );
		$this->assertNotContains( 'formentor', $this->slugs( $audi ) );
		$this->assertNotContains( 'formentor', $this->slugs( $cupra ) );
	}

	/**
	 * A 2000 Golf IV path and a 2015 Golf VII path are different vehicles.
	 * A wide SKU that unions both years and both submodels must not let year
	 * 2000 list VII Variant. Years are not copied onto every make row.
	 */
	public function test_year_2000_golf_does_not_list_vii_variant(): void {
		$this->make_product( array(
			'pa_make'      => 'Volkswagen',
			'pa_model'     => 'Golf',
			'pa_submodel'  => 'IV',
			'pa_variant'   => '1.6',
			'pa_year_alt'  => '2000',
		) );
		$this->make_product( array(
			'pa_make'      => 'Volkswagen',
			'pa_model'     => 'Golf',
			'pa_submodel'  => 'VII Variant',
			'pa_variant'   => 'R 2.0 TSI',
			'pa_year_alt'  => '2015',
		) );
		$this->make_product( array(
			'pa_make'      => array( 'Volkswagen', 'Audi' ),
			'pa_model'     => array( 'Golf', 'A3' ),
			'pa_submodel'  => array( 'IV', 'VII Variant' ),
			'pa_variant'   => array( '1.6', 'R 2.0 TSI' ),
			'pa_year_alt'  => array( '2000', '2015' ),
		) );
		YDU_Fitment_Cascade::flush_cache();

		$in_2000 = $this->cascade->get_terms_for_level( 'submodel', array(
			'year'  => '2000',
			'make'  => 'volkswagen',
			'model' => 'golf',
		) );
		$this->assertSame( array( 'iv' ), $this->slugs( $in_2000 ) );

		$in_2015 = $this->cascade->get_terms_for_level( 'submodel', array(
			'year'  => '2015',
			'make'  => 'volkswagen',
			'model' => 'golf',
		) );
		$this->assertSame( array( 'vii-variant' ), $this->slugs( $in_2015 ) );

		$variants_2000 = $this->cascade->get_terms_for_level( 'variant', array(
			'year'  => '2000',
			'make'  => 'volkswagen',
			'model' => 'golf',
		) );
		$this->assertSame( array( '1-6' ), $this->slugs( $variants_2000 ) );
	}

	public function test_models_empty_for_unknown_make(): void {
		$this->assertSame( array(), $this->cascade->get_terms_for_level( 'model', array( 'make' => 'ford' ) ) );
	}

	public function test_unknown_level_returns_empty(): void {
		$this->assertSame( array(), $this->cascade->get_terms_for_level( 'engine', array() ) );
	}

	public function test_invalid_parent_does_not_leak_other_makes_models(): void {
		// Audi has no "Golf Mk6"; combining VW-only model under Audi yields nothing.
		$subs = $this->cascade->get_terms_for_level( 'submodel', array( 'make' => 'audi', 'model' => 'golf-mk6' ) );
		$this->assertSame( array(), $this->slugs( $subs ) );
	}

	public function test_audi_variants_for_full_chain(): void {
		$audi_variants = $this->cascade->get_terms_for_level( 'variant', array(
			'make' => 'audi', 'model' => 'a3-8p', 'submodel' => 'sportback',
		) );
		$this->assertSame( array( '1-8-tfsi', '2-0-tfsi' ), $this->slugs( $audi_variants ) );
	}

	public function test_engine_code_level_filters_to_chain(): void {
		$codes = $this->cascade->get_terms_for_level( 'engine_code', array(
			'make' => 'volkswagen', 'model' => 'golf-mk5', 'submodel' => 'hatch', 'variant' => 'gti',
		) );
		$this->assertSame( array( 'bwa' ), $this->slugs( $codes ) );
	}

	public function test_model_filters_makes_and_engine_code_filters_years(): void {
		$makes = $this->cascade->get_terms_for_level( 'make', array( 'model' => 'golf-mk5' ) );
		$this->assertSame( array( 'volkswagen' ), $this->slugs( $makes ) );

		$years = $this->cascade->get_terms_for_level( 'year', array( 'engine_code' => 'bwa' ) );
		$this->assertSame( array( '2008' ), $this->slugs( $years ) );

		$makes_for_code = $this->cascade->get_terms_for_level( 'make', array( 'engine_code' => 'bwa' ) );
		$this->assertSame( array( 'audi', 'volkswagen' ), $this->slugs( $makes_for_code ) );
	}

	public function test_resolve_selects_a_level_with_one_option(): void {
		$settled = $this->cascade->resolve( array( 'model' => 'golf-mk5' ) );
		$this->assertSame( 'golf-mk5', $settled['model'] );
		$this->assertSame( 'volkswagen', $settled['make'] );
		$this->assertSame( 'hatch', $settled['submodel'] );
		$this->assertArrayNotHasKey( 'year', $settled );
		$this->assertArrayNotHasKey( 'variant', $settled );
	}

	public function test_resolve_from_engine_code_fills_the_shared_year(): void {
		$settled = $this->cascade->resolve( array( 'engine_code' => 'bwa' ) );
		$this->assertSame( 'bwa', $settled['engine_code'] );
		$this->assertSame( '2008', $settled['year'] );
		$this->assertArrayNotHasKey( 'make', $settled );
	}

	public function test_year_filtered_by_the_rest_of_the_vehicle(): void {
		$years = $this->cascade->get_terms_for_level( 'year', array(
			'make' => 'volkswagen', 'model' => 'golf-mk5', 'submodel' => 'hatch', 'variant' => 'gti', 'engine_code' => 'bwa',
		) );
		$this->assertSame( array( '2008' ), $this->slugs( $years ) );
	}

	public function test_flush_increments_cache_version(): void {
		$before = (int) get_option( YDU_Fitment_Cascade::VER_OPTION, 1 );
		YDU_Fitment_Cascade::flush_cache();
		$this->assertSame( $before + 1, (int) get_option( YDU_Fitment_Cascade::VER_OPTION ) );
	}

	public function test_catalog_change_invalidates_cache(): void {
		// Warm the cache, then add a new make; the save_post_product hook flushes,
		// so the new make must appear on the next read.
		$this->assertNotContains( 'skoda', $this->slugs( $this->cascade->get_terms_for_level( 'make' ) ) );
		$id = self::factory()->post->create( array( 'post_type' => 'product', 'post_status' => 'publish' ) );
		wp_set_object_terms( $id, 'Skoda', 'pa_make' );
		do_action( 'save_post_product', $id, get_post( $id ), true );
		$this->assertContains( 'skoda', $this->slugs( $this->cascade->get_terms_for_level( 'make' ) ) );
	}
}
