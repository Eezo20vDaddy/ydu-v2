<?php
/**
 * fitment/v1 REST endpoint tests (task 3.2, tdd:required).
 *
 * @package ydu-fitment
 */

require_once __DIR__ . '/class-ydu-fitment-testcase.php';

class Test_YDU_Fitment_REST extends YDU_Fitment_TestCase {

	protected function setUp(): void {
		parent::setUp();
		do_action( 'rest_api_init' );
	}

	private function get( string $route, array $params = array() ): WP_REST_Response {
		$request = new WP_REST_Request( 'GET', '/fitment/v1/' . $route );
		foreach ( $params as $k => $v ) {
			$request->set_param( $k, $v );
		}
		return rest_get_server()->dispatch( $request );
	}

	public function test_routes_are_registered(): void {
		$routes = rest_get_server()->get_routes();
		foreach ( array( 'makes', 'models', 'submodels', 'variants', 'engine_codes', 'years' ) as $r ) {
			$this->assertArrayHasKey( '/fitment/v1/' . $r, $routes );
		}
	}

	public function test_engine_codes_and_years_endpoints(): void {
		$codes = $this->get( 'engine_codes', array(
			'make' => 'volkswagen', 'model' => 'golf-mk5', 'submodel' => 'hatch', 'variant' => 'gti',
		) );
		$this->assertSame( 200, $codes->get_status() );
		$this->assertSame( array( 'bwa' ), array_map( static fn( $t ) => $t['slug'], $codes->get_data() ) );

		$years = $this->get( 'years', array(
			'make' => 'volkswagen', 'model' => 'golf-mk5', 'submodel' => 'hatch', 'variant' => 'gti', 'engine_code' => 'bwa',
		) );
		$this->assertSame( 200, $years->get_status() );
		$this->assertSame( array( '2008' ), array_map( static fn( $t ) => $t['slug'], $years->get_data() ) );
	}

	public function test_makes_endpoint_returns_makes(): void {
		$res = $this->get( 'makes' );
		$this->assertSame( 200, $res->get_status() );
		$slugs = array_map( static fn( $t ) => $t['slug'], $res->get_data() );
		sort( $slugs );
		$this->assertSame( array( 'audi', 'volkswagen' ), $slugs );
	}

	public function test_models_endpoint_filters_by_make(): void {
		$res = $this->get( 'models', array( 'make' => 'volkswagen' ) );
		$this->assertSame( 200, $res->get_status() );
		$slugs = array_map( static fn( $t ) => $t['slug'], $res->get_data() );
		sort( $slugs );
		$this->assertSame( array( 'golf-mk5', 'golf-mk6' ), $slugs );
	}

	public function test_sends_cache_header(): void {
		$res = $this->get( 'makes' );
		$headers = $res->get_headers();
		$this->assertArrayHasKey( 'Cache-Control', $headers );
		$this->assertStringContainsString( 'max-age=3600', $headers['Cache-Control'] );
	}

	public function test_models_requires_make_param(): void {
		// Missing required 'make' → 400 from the REST args validation.
		$res = $this->get( 'models' );
		$this->assertSame( 400, $res->get_status() );
	}

	public function test_variants_endpoint_full_chain(): void {
		$res = $this->get( 'variants', array(
			'make' => 'volkswagen', 'model' => 'golf-mk5', 'submodel' => 'hatch',
		) );
		$this->assertSame( 200, $res->get_status() );
		$slugs = array_map( static fn( $t ) => $t['slug'], $res->get_data() );
		sort( $slugs );
		$this->assertSame( array( '2-0-fsi', 'gti' ), $slugs );
	}

	public function test_unknown_parent_returns_empty_200(): void {
		$res = $this->get( 'models', array( 'make' => 'ford' ) );
		$this->assertSame( 200, $res->get_status() );
		$this->assertSame( array(), $res->get_data() );
	}
}
