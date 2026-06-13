<?php
/**
 * Per-customer per-product price store. One row per (customer_id, product_id)
 * holding the last price that customer paid, plus provenance for the Zoho loop.
 *
 * @package ydu-trade
 */

defined( 'ABSPATH' ) || exit;

class YDU_Trade_Store {

	const DB_VERSION_OPTION = 'ydu_trade_db_version';
	const DB_VERSION        = '1';

	public static function table(): string {
		global $wpdb;
		return $wpdb->prefix . 'ydu_trade_prices';
	}

	public static function install_table(): void {
		global $wpdb;
		$table   = self::table();
		$charset = $wpdb->get_charset_collate();

		// dbDelta-compatible schema. Unique key enforces one price per customer+product.
		$sql = "CREATE TABLE {$table} (
			id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
			customer_id BIGINT UNSIGNED NOT NULL,
			product_id BIGINT UNSIGNED NOT NULL,
			price DECIMAL(19,4) NOT NULL,
			currency VARCHAR(3) NOT NULL DEFAULT 'AUD',
			source VARCHAR(40) NOT NULL DEFAULT 'manual',
			zoho_reference VARCHAR(64) NULL,
			updated_at DATETIME NOT NULL,
			PRIMARY KEY  (id),
			UNIQUE KEY customer_product (customer_id, product_id),
			KEY customer_id (customer_id)
		) {$charset};";

		require_once ABSPATH . 'wp-admin/includes/upgrade.php';
		dbDelta( $sql );
		update_option( self::DB_VERSION_OPTION, self::DB_VERSION, false );
	}

	public static function maybe_upgrade(): void {
		if ( get_option( self::DB_VERSION_OPTION ) !== self::DB_VERSION ) {
			self::install_table();
		}
	}

	/**
	 * The customer's stored price for a product, or null if none.
	 *
	 * @return float|null
	 */
	public static function get_price( int $customer_id, int $product_id ): ?float {
		if ( $customer_id <= 0 || $product_id <= 0 ) {
			return null;
		}
		global $wpdb;
		$table = self::table();
		$value = $wpdb->get_var( $wpdb->prepare( // phpcs:ignore WordPress.DB
			"SELECT price FROM {$table} WHERE customer_id = %d AND product_id = %d", // phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
			$customer_id,
			$product_id
		) );
		return null === $value ? null : (float) $value;
	}

	/**
	 * Upsert a customer's last-paid price for a product. This is the ingestion
	 * entry point for the Zoho feedback loop.
	 *
	 * @return bool True on success.
	 */
	public static function set_price( int $customer_id, int $product_id, float $price, string $source = 'manual', ?string $zoho_reference = null ): bool {
		if ( $customer_id <= 0 || $product_id <= 0 || $price < 0 ) {
			return false;
		}
		global $wpdb;
		$result = $wpdb->replace( // phpcs:ignore WordPress.DB.DirectDatabaseQuery
			self::table(),
			array(
				'customer_id'    => $customer_id,
				'product_id'     => $product_id,
				'price'          => $price,
				'currency'       => function_exists( 'get_woocommerce_currency' ) ? get_woocommerce_currency() : 'AUD',
				'source'         => substr( $source, 0, 40 ),
				'zoho_reference' => $zoho_reference,
				'updated_at'     => current_time( 'mysql', true ),
			),
			array( '%d', '%d', '%f', '%s', '%s', '%s', '%s' )
		);
		return false !== $result;
	}

	/** Remove a stored price (e.g. revert a customer/item to standard). */
	public static function delete_price( int $customer_id, int $product_id ): bool {
		global $wpdb;
		return false !== $wpdb->delete( // phpcs:ignore WordPress.DB.DirectDatabaseQuery
			self::table(),
			array( 'customer_id' => $customer_id, 'product_id' => $product_id ),
			array( '%d', '%d' )
		);
	}
}
