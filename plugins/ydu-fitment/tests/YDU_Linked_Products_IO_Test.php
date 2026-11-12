<?php
/**
 * Linked-product import/export mapping.
 *
 * @package ydu-fitment
 */

require_once __DIR__ . '/class-ydu-fitment-testcase.php';

class YDU_Linked_Products_IO_Test extends YDU_Fitment_TestCase {

	public function test_tokens_split_on_pipe_and_comma(): void {
		$this->assertSame( array( '03L198119B', '03L198119F' ), ydu_linked_product_tokens( '03L198119B|03L198119F' ) );
		$this->assertSame( array( '12', '34' ), ydu_linked_product_tokens( '["12","34"]' ) );
		$this->assertSame( array(), ydu_linked_product_tokens( '' ) );
	}

	public function test_mapping_labels_name_the_linked_products(): void {
		$fields = array(
			'upsell_ids'    => array( 'title' => 'Related products: Upsell IDs', 'description' => 'old' ),
			'crosssell_ids' => 'Cross-sells',
			'children'      => array( 'title' => 'Child product ID', 'description' => 'old' ),
			'sku'           => array( 'title' => 'SKU', 'description' => 'SKU' ),
		);

		$mapped = ydu_linked_product_mapping_fields( $fields );

		$this->assertSame( 'Linked products: Upsells', $mapped['upsell_ids']['title'] );
		$this->assertContains( 'Upsells', $mapped['upsell_ids']['similar_fields'] );
		$this->assertSame( 'Linked products: Cross-sells', $mapped['crosssell_ids'] );
		$this->assertSame( 'Linked products: Grouped children', $mapped['children']['title'] );
		$this->assertSame( 'SKU', $mapped['sku']['title'] );
	}
}
