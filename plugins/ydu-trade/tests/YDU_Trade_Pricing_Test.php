<?php
/**
 * Trade pricing display-substitution tests. Requires WooCommerce; skips
 * gracefully if WC isn't loaded in the test environment.
 *
 * @package ydu-trade
 */

class YDU_Trade_Pricing_Test extends WP_UnitTestCase {

	protected function setUp(): void {
		parent::setUp();
		if ( ! class_exists( 'WooCommerce' ) || ! class_exists( 'WC_Product_Simple' ) ) {
			$this->markTestSkipped( 'WooCommerce not loaded.' );
		}
		global $wpdb;
		$wpdb->query( 'TRUNCATE TABLE ' . YDU_Trade_Store::table() ); // phpcs:ignore
	}

	private function make_product( float $regular ): int {
		$p = new WC_Product_Simple();
		$p->set_regular_price( (string) $regular );
		$p->set_price( (string) $regular );
		return $p->save();
	}

	public function test_retail_user_sees_standard_price(): void {
		$pid = $this->make_product( 100.00 );
		$uid = self::factory()->user->create( array( 'role' => 'customer' ) );
		wp_set_current_user( $uid );
		YDU_Trade_Store::set_price( $uid, $pid, 60.00 ); // even with a stored row…
		// …a non-trade role must not get the trade price.
		$this->assertEquals( 100.00, (float) wc_get_product( $pid )->get_price() );
	}

	public function test_trade_user_with_price_sees_individual_price(): void {
		$pid = $this->make_product( 100.00 );
		$uid = self::factory()->user->create( array( 'role' => 'trade' ) );
		wp_set_current_user( $uid );
		YDU_Trade_Store::set_price( $uid, $pid, 72.00, 'zoho' );
		$this->assertEquals( 72.00, (float) wc_get_product( $pid )->get_price() );
	}

	public function test_trade_user_without_price_sees_standard(): void {
		$pid = $this->make_product( 100.00 );
		$uid = self::factory()->user->create( array( 'role' => 'trade' ) );
		wp_set_current_user( $uid );
		$this->assertEquals( 100.00, (float) wc_get_product( $pid )->get_price() );
	}

	public function test_trade_price_is_per_customer(): void {
		$pid = $this->make_product( 100.00 );
		$a = self::factory()->user->create( array( 'role' => 'trade' ) );
		$b = self::factory()->user->create( array( 'role' => 'trade' ) );
		YDU_Trade_Store::set_price( $a, $pid, 55.00 );
		wp_set_current_user( $b );
		$this->assertEquals( 100.00, (float) wc_get_product( $pid )->get_price(), 'customer B has no price → standard' );
		wp_set_current_user( $a );
		$this->assertEquals( 55.00, (float) wc_get_product( $pid )->get_price() );
	}
}
