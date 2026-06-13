<?php
/**
 * Trade price store tests — no WooCommerce required.
 *
 * @package ydu-trade
 */

class Test_YDU_Trade_Store extends WP_UnitTestCase {

	protected function setUp(): void {
		parent::setUp();
		global $wpdb;
		$wpdb->query( 'TRUNCATE TABLE ' . YDU_Trade_Store::table() ); // phpcs:ignore
	}

	public function test_get_returns_null_when_no_price(): void {
		$this->assertNull( YDU_Trade_Store::get_price( 10, 20 ) );
	}

	public function test_set_then_get_roundtrips(): void {
		$this->assertTrue( YDU_Trade_Store::set_price( 10, 20, 123.45, 'zoho', 'SO-001' ) );
		$this->assertSame( 123.45, YDU_Trade_Store::get_price( 10, 20 ) );
	}

	public function test_set_upserts_one_row_per_customer_product(): void {
		YDU_Trade_Store::set_price( 10, 20, 100.00 );
		YDU_Trade_Store::set_price( 10, 20, 80.00, 'zoho', 'SO-009' );
		$this->assertSame( 80.00, YDU_Trade_Store::get_price( 10, 20 ) );

		global $wpdb;
		$count = (int) $wpdb->get_var( 'SELECT COUNT(*) FROM ' . YDU_Trade_Store::table() . ' WHERE customer_id = 10 AND product_id = 20' ); // phpcs:ignore
		$this->assertSame( 1, $count, 'unique key must keep a single row per customer+product' );
	}

	public function test_prices_are_isolated_per_customer(): void {
		YDU_Trade_Store::set_price( 10, 20, 50.00 );
		YDU_Trade_Store::set_price( 11, 20, 70.00 );
		$this->assertSame( 50.00, YDU_Trade_Store::get_price( 10, 20 ) );
		$this->assertSame( 70.00, YDU_Trade_Store::get_price( 11, 20 ) );
	}

	public function test_delete_reverts_to_standard(): void {
		YDU_Trade_Store::set_price( 10, 20, 50.00 );
		$this->assertTrue( YDU_Trade_Store::delete_price( 10, 20 ) );
		$this->assertNull( YDU_Trade_Store::get_price( 10, 20 ) );
	}

	public function test_invalid_input_rejected(): void {
		$this->assertFalse( YDU_Trade_Store::set_price( 0, 20, 10.00 ) );
		$this->assertFalse( YDU_Trade_Store::set_price( 10, 0, 10.00 ) );
		$this->assertFalse( YDU_Trade_Store::set_price( 10, 20, -5.00 ) );
	}
}
