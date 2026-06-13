<?php
/**
 * Cascade query-layer tests (task 3.1, tdd:required).
 *
 * @package ydu-fitment
 */

require_once __DIR__ . '/class-ydu-fitment-testcase.php';

class Test_YDU_Fitment_Cascade extends YDU_Fitment_TestCase {

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

	public function test_multifit_part_creates_documented_cross_make_leak(): void {
		// Faithful to the flat-attribute model (and the live site): a part tagged
		// for two makes/models makes the "other" model reachable under each make.
		// This is the documented co-occurrence quirk, not a bug — asserted so any
		// future change to the semantics is caught.
		$this->add_multifit_part();
		$vw_models = $this->cascade->get_terms_for_level( 'model', array( 'make' => 'volkswagen' ) );
		$this->assertContains( 'a3-8p', $this->slugs( $vw_models ) );
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

	public function test_year_is_the_final_level(): void {
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
