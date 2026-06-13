<?php
/**
 * fitment/v1 REST endpoints — public, GET-only, cacheable. One route per cascade
 * level; each requires its ancestor slugs as query args.
 *
 * Routes:
 *   GET /fitment/v1/makes
 *   GET /fitment/v1/models?make=<slug>
 *   GET /fitment/v1/submodels?make=<slug>&model=<slug>
 *   GET /fitment/v1/variants?make=<slug>&model=<slug>&submodel=<slug>
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
		foreach ( $this->route_map() as $route => $config ) {
			$args = array();
			foreach ( $config['parents'] as $parent ) {
				$args[ $parent ] = array(
					'required'          => true,
					'type'              => 'string',
					'sanitize_callback' => 'sanitize_title',
					'validate_callback' => static function ( $value ) {
						return is_string( $value ) && '' !== trim( $value );
					},
				);
			}

			register_rest_route(
				self::NAMESPACE,
				'/' . $route,
				array(
					'methods'             => WP_REST_Server::READABLE,
					'callback'            => function ( WP_REST_Request $request ) use ( $config ) {
						return $this->handle( $config['level'], $config['parents'], $request );
					},
					'permission_callback' => '__return_true', // public read-only fitment data
					'args'                => $args,
				)
			);
		}
	}

	private function handle( string $level, array $parent_keys, WP_REST_Request $request ) {
		$parents = array();
		foreach ( $parent_keys as $key ) {
			$parents[ $key ] = (string) $request->get_param( $key );
		}

		$cascade = new YDU_Fitment_Cascade();
		$terms   = $cascade->get_terms_for_level( $level, $parents );

		$response = new WP_REST_Response( $terms, 200 );
		// Public, cacheable for an hour at the edge; cleared server-side on catalog change.
		$response->header( 'Cache-Control', 'public, max-age=3600' );
		return $response;
	}
}
