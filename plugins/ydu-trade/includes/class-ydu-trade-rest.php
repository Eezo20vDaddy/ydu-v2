<?php
/**
 * Authenticated ingestion endpoint — the defined entry point for the Zoho
 * feedback loop. The Zoho sync (separate task, needs Zoho API credentials)
 * authenticates as a manage_woocommerce user (Application Password) and POSTs a
 * customer's last-paid price for a product here.
 *
 *   POST /trade/v1/price   { customer_id|customer_email, product_id|sku, price, source?, zoho_reference? }
 *   GET  /trade/v1/price?customer_id=&product_id=   (read-back, same capability)
 *
 * @package ydu-trade
 */

defined( 'ABSPATH' ) || exit;

class YDU_Trade_REST {

	const NAMESPACE = 'trade/v1';

	public function register_routes(): void {
		register_rest_route( self::NAMESPACE, '/price', array(
			array(
				'methods'             => WP_REST_Server::CREATABLE,
				'callback'            => array( $this, 'set_price' ),
				'permission_callback' => array( $this, 'can_manage' ),
				'args'                => array(
					'customer_id'    => array( 'type' => 'integer', 'sanitize_callback' => 'absint' ),
					'customer_email' => array( 'type' => 'string', 'sanitize_callback' => 'sanitize_email' ),
					'product_id'     => array( 'type' => 'integer', 'sanitize_callback' => 'absint' ),
					'sku'            => array( 'type' => 'string', 'sanitize_callback' => 'sanitize_text_field' ),
					'price'          => array( 'required' => true, 'type' => 'number' ),
					'source'         => array( 'type' => 'string', 'sanitize_callback' => 'sanitize_text_field', 'default' => 'zoho' ),
					'zoho_reference' => array( 'type' => 'string', 'sanitize_callback' => 'sanitize_text_field' ),
				),
			),
			array(
				'methods'             => WP_REST_Server::READABLE,
				'callback'            => array( $this, 'get_price' ),
				'permission_callback' => array( $this, 'can_manage' ),
				'args'                => array(
					'customer_id' => array( 'required' => true, 'type' => 'integer', 'sanitize_callback' => 'absint' ),
					'product_id'  => array( 'required' => true, 'type' => 'integer', 'sanitize_callback' => 'absint' ),
				),
			),
		) );
	}

	public function can_manage(): bool {
		return current_user_can( 'manage_woocommerce' );
	}

	private function resolve_customer( WP_REST_Request $r ): int {
		$id = (int) $r->get_param( 'customer_id' );
		if ( $id > 0 ) {
			return $id;
		}
		$email = (string) $r->get_param( 'customer_email' );
		if ( $email ) {
			$user = get_user_by( 'email', $email );
			if ( $user ) {
				return (int) $user->ID;
			}
		}
		return 0;
	}

	private function resolve_product( WP_REST_Request $r ): int {
		$id = (int) $r->get_param( 'product_id' );
		if ( $id > 0 ) {
			return $id;
		}
		$sku = (string) $r->get_param( 'sku' );
		if ( $sku ) {
			return (int) wc_get_product_id_by_sku( $sku );
		}
		return 0;
	}

	public function set_price( WP_REST_Request $request ) {
		$customer_id = $this->resolve_customer( $request );
		$product_id  = $this->resolve_product( $request );
		$price       = (float) $request->get_param( 'price' );

		if ( $customer_id <= 0 ) {
			return new WP_Error( 'ydu_trade_no_customer', __( 'Unknown customer (provide customer_id or a registered customer_email).', 'ydu-trade' ), array( 'status' => 400 ) );
		}
		if ( $product_id <= 0 ) {
			return new WP_Error( 'ydu_trade_no_product', __( 'Unknown product (provide product_id or a known sku).', 'ydu-trade' ), array( 'status' => 400 ) );
		}
		if ( $price < 0 ) {
			return new WP_Error( 'ydu_trade_bad_price', __( 'Price must be zero or positive.', 'ydu-trade' ), array( 'status' => 400 ) );
		}

		$ok = YDU_Trade_Store::set_price(
			$customer_id,
			$product_id,
			$price,
			(string) $request->get_param( 'source' ),
			$request->get_param( 'zoho_reference' )
		);

		if ( ! $ok ) {
			return new WP_Error( 'ydu_trade_write_failed', __( 'Could not store price.', 'ydu-trade' ), array( 'status' => 500 ) );
		}
		return new WP_REST_Response( array(
			'stored'      => true,
			'customer_id' => $customer_id,
			'product_id'  => $product_id,
			'price'       => $price,
		), 200 );
	}

	public function get_price( WP_REST_Request $request ) {
		$price = YDU_Trade_Store::get_price(
			(int) $request->get_param( 'customer_id' ),
			(int) $request->get_param( 'product_id' )
		);
		return new WP_REST_Response( array( 'price' => $price ), 200 );
	}
}
