<?php
/**
 * Trade ingestion REST tests — the Zoho feedback entry point. No WooCommerce
 * needed (uses explicit customer_id/product_id; capability granted directly).
 *
 * @package ydu-trade
 */

class Test_YDU_Trade_REST extends WP_UnitTestCase {

	protected function setUp(): void {
		parent::setUp();
		global $wpdb;
		$wpdb->query( 'TRUNCATE TABLE ' . YDU_Trade_Store::table() ); // phpcs:ignore
		do_action( 'rest_api_init' );
	}

	private function as_manager(): int {
		$uid = self::factory()->user->create( array( 'role' => 'administrator' ) );
		$user = get_userdata( $uid );
		$user->add_cap( 'manage_woocommerce' );
		wp_set_current_user( $uid );
		return $uid;
	}

	private function post( array $body ): WP_REST_Response {
		$r = new WP_REST_Request( 'POST', '/trade/v1/price' );
		foreach ( $body as $k => $v ) {
			$r->set_param( $k, $v );
		}
		return rest_get_server()->dispatch( $r );
	}

	public function test_requires_capability(): void {
		wp_set_current_user( self::factory()->user->create( array( 'role' => 'subscriber' ) ) );
		$res = $this->post( array( 'customer_id' => 5, 'product_id' => 6, 'price' => 10 ) );
		$this->assertTrue( in_array( $res->get_status(), array( 401, 403 ), true ), 'subscriber must be denied' );
		$this->assertNull( YDU_Trade_Store::get_price( 5, 6 ), 'no price should be stored on denial' );
	}

	public function test_manager_can_store_price(): void {
		$this->as_manager();
		$res = $this->post( array( 'customer_id' => 5, 'product_id' => 6, 'price' => 42.50, 'source' => 'zoho', 'zoho_reference' => 'INV-77' ) );
		$this->assertSame( 200, $res->get_status() );
		$this->assertTrue( $res->get_data()['stored'] );
		$this->assertSame( 42.50, YDU_Trade_Store::get_price( 5, 6 ) );
	}

	public function test_rejects_missing_customer(): void {
		$this->as_manager();
		$res = $this->post( array( 'product_id' => 6, 'price' => 10 ) );
		$this->assertSame( 400, $res->get_status() );
	}

	public function test_rejects_missing_product(): void {
		$this->as_manager();
		$res = $this->post( array( 'customer_id' => 5, 'price' => 10 ) );
		$this->assertSame( 400, $res->get_status() );
	}

	public function test_resolves_customer_by_email(): void {
		$this->as_manager();
		$cid = self::factory()->user->create( array( 'role' => 'trade', 'user_email' => 'shop@example.test' ) );
		$res = $this->post( array( 'customer_email' => 'shop@example.test', 'product_id' => 6, 'price' => 30 ) );
		$this->assertSame( 200, $res->get_status() );
		$this->assertSame( 30.0, YDU_Trade_Store::get_price( $cid, 6 ) );
	}
}
