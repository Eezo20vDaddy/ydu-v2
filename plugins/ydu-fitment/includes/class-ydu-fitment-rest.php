<?php
/**
 * fitment/v1 REST endpoints — public, GET-only, cacheable.
 * GET /fitment/v1/index is the catalog the finder filters locally.
 * The per-level routes accept any other level as an optional constraint.
 *
 * @package ydu-fitment
 */

defined( 'ABSPATH' ) || exit;

class YDU_Fitment_REST {

	const NAMESPACE = 'fitment/v1';

	/** route slug => [ level, required-ancestor-level-keys ] */
	private function route_map(): array {
		return array(
			'makes'        => array( 'level' => 'make', 'parents' => array() ),
			'models'       => array( 'level' => 'model', 'parents' => array( 'make' ) ),
			'submodels'    => array( 'level' => 'submodel', 'parents' => array( 'make', 'model' ) ),
			'variants'     => array( 'level' => 'variant', 'parents' => array( 'make', 'model', 'submodel' ) ),
			'engine_codes' => array( 'level' => 'engine_code', 'parents' => array( 'make', 'model', 'submodel', 'variant' ) ),
			'years'        => array( 'level' => 'year', 'parents' => array( 'make', 'model', 'submodel', 'variant', 'engine_code' ) ),
		);
	}

	public function register_routes(): void {
		register_rest_route(
			self::NAMESPACE,
			'/index',
			array(
				'methods'             => WP_REST_Server::READABLE,
				'callback'            => array( $this, 'index' ),
				'permission_callback' => '__return_true',
			)
		);

		$level_keys = array_keys( ydu_fitment_levels() );
		foreach ( $this->route_map() as $route => $config ) {
			$args = array();
			foreach ( $level_keys as $key ) {
				if ( $key === $config['level'] ) {
					continue;
				}
				$args[ $key ] = array(
					'required'          => false,
					'type'              => 'string',
					'sanitize_callback' => 'sanitize_title',
				);
			}

			register_rest_route(
				self::NAMESPACE,
				'/' . $route,
				array(
					'methods'             => WP_REST_Server::READABLE,
					'callback'            => function ( WP_REST_Request $request ) use ( $config, $level_keys ) {
						return $this->handle( $config['level'], $level_keys, $request );
					},
					'permission_callback' => '__return_true',
					'args'                => $args,
				)
			);
		}
	}

	public function index(): WP_REST_Response {
		$cascade = new YDU_Fitment_Cascade();
		$data    = $cascade->index();
		$data['version'] = (int) get_option( YDU_Fitment_Cascade::VER_OPTION, 1 );
		$response = new WP_REST_Response( $data, 200 );
		return self::cacheable_response( $response );
	}

	private function handle( string $level, array $parent_keys, WP_REST_Request $request ) {
		$parents = array();
		foreach ( $parent_keys as $key ) {
			$value = $request->get_param( $key );
			if ( is_string( $value ) && '' !== $value ) {
				$parents[ $key ] = $value;
			}
		}

		$cascade = new YDU_Fitment_Cascade();
		$terms   = $cascade->get_terms_for_level( $level, $parents );

		$response = new WP_REST_Response( $terms, 200 );
		return self::cacheable_response( $response );
	}

	/**
	 * Cache headers for public fitment reads. Short TTL + SWR avoids edge caches
	 * serving empty/stale JSON while the cold index builds.
	 */
	private static function cacheable_response( WP_REST_Response $response ): WP_REST_Response {
		$response->header( 'Cache-Control', 'public, max-age=60, stale-while-revalidate=300' );
		return $response;
	}
}
