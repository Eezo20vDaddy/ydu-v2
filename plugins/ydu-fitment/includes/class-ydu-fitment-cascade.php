<?php
/**
 * Fitment index. One cached copy of each product's six term sets. Any selected
 * level filters the others. A level with one remaining name is the selection.
 *
 * @package ydu-fitment
 */

defined( 'ABSPATH' ) || exit;

class YDU_Fitment_Cascade {

	const CACHE_TTL = DAY_IN_SECONDS;
	const VER_OPTION = 'ydu_fitment_cache_ver';

	/**
	 * One index for the whole catalog: terms per level, and each product's slug sets.
	 *
	 * @return array{terms: array<string, array<int, array{id:int,name:string,slug:string}>>, rows: array<int, array<string, string[]>>}
	 */
	public function index(): array {
		$version = (int) get_option( self::VER_OPTION, 1 );
		$key     = 'ydu_fit_index_' . $version;
		$cached  = get_transient( $key );
		if ( is_array( $cached ) && isset( $cached['terms'], $cached['rows'] ) ) {
			return $cached;
		}

		$index = $this->build_index();
		set_transient( $key, $index, self::CACHE_TTL );
		return $index;
	}

	/** Product meta: aligned fitment applications (array of level => name rows from Catalog Studio). */
	const APPLICATIONS_META = '_ydu_fitment_applications';

	/**
	 * Build the in-memory fitment index from published products (cold path).
	 *
	 * Products often carry a union of every make, model, and year on one SKU.
	 * One row for that union lets any selected year pair with every submodel the
	 * make owns. Rows are therefore aligned paths that actually occur together.
	 *
	 * A stored application is one path. A single-make product is one path per
	 * year, model, and submodel it lists together: a Golf VII submodel is listed
	 * only for the years that product also has. Variant and engine slugs on that
	 * row are the ones on the same product. They are not crossed into a vehicle
	 * per code — the flat attributes do not record that — and they cannot move
	 * onto another product's year or model.
	 *
	 * A multi-make union is not a path. Its years are not copied onto a make,
	 * and its models are not copied onto a make that does not list them alone
	 * (an Audi-only model stays off Cupra; a model nobody lists alone is dropped).
	 *
	 * @return array{terms: array<string, array<int, array{id:int,name:string,slug:string}>>, rows: array<int, array<string, string[]>>}
	 */
	private function build_index(): array {
		$levels     = ydu_fitment_levels();
		$level_keys = array_keys( $levels );
		$query      = new WP_Query(
			array(
				'post_type'              => 'product',
				'post_status'            => 'publish',
				'fields'                 => 'ids',
				'posts_per_page'         => -1,
				'no_found_rows'          => true,
				'update_post_meta_cache' => true,
				'update_post_term_cache' => true,
			)
		);
		$ids = array_map( 'intval', $query->posts );

		$terms         = array();
		$product_sets  = array();
		$name_to_slug  = array();
		foreach ( $ids as $id ) {
			$product_sets[ $id ] = array_fill_keys( $level_keys, array() );
		}

		foreach ( $levels as $level => $def ) {
			$found = array();
			if ( $ids && taxonomy_exists( $def['taxonomy'] ) ) {
				$found = wp_get_object_terms(
					$ids,
					$def['taxonomy'],
					array( 'fields' => 'all_with_object_id' )
				);
				if ( is_wp_error( $found ) ) {
					$found = array();
				}
			}
			$list = array();
			$seen = array();
			$on   = array();
			foreach ( $found as $term ) {
				$tid = (int) $term->term_id;
				if ( ! isset( $seen[ $tid ] ) ) {
					$seen[ $tid ] = true;
					$list[]       = array(
						'id'   => $tid,
						'name' => $term->name,
						'slug' => $term->slug,
					);
					$name_to_slug[ $level ][ strtolower( $term->name ) ] = $term->slug;
					$name_to_slug[ $level ][ $term->slug ]             = $term->slug;
				}
				$object_id = (int) ( $term->object_id ?? 0 );
				if ( $object_id ) {
					$on[ $object_id ][] = $term->slug;
				}
			}
			if ( 'year' === $level ) {
				usort(
					$list,
					static function ( $a, $b ) {
						return strnatcmp( $a['name'], $b['name'] );
					}
				);
			}
			$terms[ $level ] = $list;
			foreach ( $ids as $id ) {
				$product_sets[ $id ][ $level ] = array_values( array_unique( $on[ $id ] ?? array() ) );
			}
		}

		$bucket = array();
		foreach ( $ids as $id ) {
			$apps = get_post_meta( $id, self::APPLICATIONS_META, true );
			if ( is_array( $apps ) && $apps !== array() ) {
				foreach ( $apps as $app ) {
					if ( ! is_array( $app ) ) {
						continue;
					}
					$row = $this->row_from_application_names( $app, $level_keys, $name_to_slug );
					if ( $row !== null ) {
						$this->remember_path( $bucket, $row );
					}
				}
				continue;
			}

			$set   = $product_sets[ $id ];
			$makes = $set['make'] ?? array();
			if ( 1 !== count( $makes ) ) {
				continue;
			}
			foreach ( $this->paths_for_single_make( $set ) as $row ) {
				$this->remember_path( $bucket, $row );
			}
		}

		$rows = array();
		foreach ( $bucket as $row ) {
			$rows[] = $this->finish_path( $row );
		}

		return array(
			'terms' => $terms,
			'rows'  => $rows,
		);
	}

	/**
	 * @param array<string, mixed>     $app
	 * @param string[]                 $level_keys
	 * @param array<string, array<string, string>> $name_to_slug
	 * @return array<string, string[]>|null
	 */
	private function row_from_application_names( array $app, array $level_keys, array $name_to_slug ): ?array {
		$row = array_fill_keys( $level_keys, array() );
		foreach ( $level_keys as $level ) {
			$raw = $app[ $level ] ?? '';
			if ( is_array( $raw ) || is_object( $raw ) ) {
				continue;
			}
			$val = trim( (string) $raw );
			if ( '' === $val ) {
				continue;
			}
			$key  = strtolower( $val );
			$slug = $name_to_slug[ $level ][ $key ] ?? sanitize_title( $val );
			if ( '' !== $slug ) {
				$row[ $level ] = array( $slug );
			}
		}
		if ( array() === array_filter( $row ) ) {
			return null;
		}
		return $row;
	}

	/**
	 * One single-make product: a separate path for each year, model, and submodel
	 * it lists. Those are not collapsed onto one make row, so a year cannot see
	 * a submodel that this product does not also carry, and a model cannot see
	 * another model's submodels from a different path.
	 *
	 * Variant and engine stay the sets on this product that share the path.
	 * Crossing every variant with every engine would invent millions of vehicles.
	 *
	 * @param array<string, string[]> $set Exactly one make slug.
	 * @return array<int, array<string, string[]>>
	 */
	private function paths_for_single_make( array $set ): array {
		$make = $set['make'][0] ?? '';
		if ( '' === $make ) {
			return array();
		}
		$variants = array_values( $set['variant'] ?? array() );
		$engines  = array_values( $set['engine_code'] ?? array() );
		$out      = array();
		foreach ( $this->axis( $set['year'] ?? array() ) as $year ) {
			foreach ( $this->axis( $set['model'] ?? array() ) as $model ) {
				foreach ( $this->axis( $set['submodel'] ?? array() ) as $submodel ) {
					$out[] = array(
						'year'        => $this->slug_list( $year ),
						'make'        => array( $make ),
						'model'       => $this->slug_list( $model ),
						'submodel'    => $this->slug_list( $submodel ),
						'variant'     => $variants,
						'engine_code' => $engines,
					);
				}
			}
		}
		return $out;
	}

	/**
	 * One pass per slug. An empty level still yields one path with that level blank.
	 *
	 * @param string[] $slugs
	 * @return array<int, string|null>
	 */
	private function axis( array $slugs ): array {
		return $slugs === array() ? array( null ) : array_values( $slugs );
	}

	/**
	 * @return string[]
	 */
	private function slug_list( ?string $slug ): array {
		return ( null === $slug || '' === $slug ) ? array() : array( $slug );
	}

	/**
	 * Fold paths that share year, make, model, and submodel. Variants and engine
	 * codes are the union of the single-make products that have that path.
	 *
	 * @param array<string, array{year: string[], make: string[], model: string[], submodel: string[], variant: array<string, true>, engine_code: array<string, true>}> $bucket
	 * @param array<string, string[]> $row
	 */
	private function remember_path( array &$bucket, array $row ): void {
		$key = implode(
			"\0",
			array(
				$row['year'][0] ?? '',
				$row['make'][0] ?? '',
				$row['model'][0] ?? '',
				$row['submodel'][0] ?? '',
			)
		);
		if ( ! isset( $bucket[ $key ] ) ) {
			$bucket[ $key ] = array(
				'year'        => $this->slug_list( $row['year'][0] ?? '' ),
				'make'        => $this->slug_list( $row['make'][0] ?? '' ),
				'model'       => $this->slug_list( $row['model'][0] ?? '' ),
				'submodel'    => $this->slug_list( $row['submodel'][0] ?? '' ),
				'variant'     => array(),
				'engine_code' => array(),
			);
		}
		foreach ( array( 'variant', 'engine_code' ) as $level ) {
			foreach ( $row[ $level ] ?? array() as $slug ) {
				if ( '' !== $slug ) {
					$bucket[ $key ][ $level ][ $slug ] = true;
				}
			}
		}
	}

	/**
	 * @param array{year: string[], make: string[], model: string[], submodel: string[], variant: array<string, true>, engine_code: array<string, true>} $row
	 * @return array<string, string[]>
	 */
	private function finish_path( array $row ): array {
		$row['variant']     = array_keys( $row['variant'] );
		$row['engine_code'] = array_keys( $row['engine_code'] );
		return $row;
	}

	/**
	 * Terms at $level that share a product with every selected slug.
	 *
	 * @param array<string,string> $parents Any other levels, not only those to the left.
	 * @return array<int,array{id:int,name:string,slug:string}>
	 */
	public function get_terms_for_level( string $level, array $parents = array() ): array {
		if ( ! isset( ydu_fitment_levels()[ $level ] ) ) {
			return array();
		}
		$parents = $this->clean_selection( $parents );
		unset( $parents[ $level ] );

		$index   = $this->index();
		$present = array();
		foreach ( $index['rows'] as $row ) {
			foreach ( $parents as $key => $slug ) {
				if ( ! in_array( $slug, $row[ $key ] ?? array(), true ) ) {
					continue 2;
				}
			}
			foreach ( $row[ $level ] ?? array() as $slug ) {
				$present[ $slug ] = true;
			}
		}

		$out = array();
		foreach ( $index['terms'][ $level ] as $term ) {
			if ( isset( $present[ $term['slug'] ] ) ) {
				$out[] = $term;
			}
		}
		return $out;
	}

	/**
	 * Keep the user's choices and fill any level that has exactly one remaining option.
	 *
	 * @param array<string,string> $selected
	 * @return array<string,string>
	 */
	public function resolve( array $selected ): array {
		$clean = $this->clean_selection( $selected );
		$keys  = array_keys( ydu_fitment_levels() );
		for ( $pass = 0; $pass < count( $keys ); $pass++ ) {
			$changed = false;
			foreach ( $keys as $level ) {
				$constraints = $clean;
				unset( $constraints[ $level ] );
				$slugs = array_column( $this->get_terms_for_level( $level, $constraints ), 'slug' );
				if ( isset( $clean[ $level ] ) && ! in_array( $clean[ $level ], $slugs, true ) ) {
					unset( $clean[ $level ] );
					$changed = true;
				}
				if ( 1 === count( $slugs ) && ( $clean[ $level ] ?? '' ) !== $slugs[0] ) {
					$clean[ $level ] = $slugs[0];
					$changed         = true;
				}
			}
			if ( ! $changed ) {
				break;
			}
		}
		return $clean;
	}

	/**
	 * @param array<string,mixed> $selected
	 * @return array<string,string>
	 */
	private function clean_selection( array $selected ): array {
		$clean = array();
		foreach ( array_keys( ydu_fitment_levels() ) as $level ) {
			if ( ! empty( $selected[ $level ] ) ) {
				$clean[ $level ] = sanitize_title( (string) $selected[ $level ] );
			}
		}
		return $clean;
	}

	/**
	 * Invalidate all cached cascade results by bumping the cache-key version.
	 * Old transients are abandoned and expire via TTL. This is cache-correct
	 * (no stale options-cache reads) and uses no direct SQL.
	 */
	public static function flush_cache(): void {
		$version = (int) get_option( self::VER_OPTION, 1 );
		update_option( self::VER_OPTION, $version + 1, false );
	}
}

// Invalidate cache when the catalog changes.
add_action( 'save_post_product', array( 'YDU_Fitment_Cascade', 'flush_cache' ) );
add_action( 'woocommerce_update_product', array( 'YDU_Fitment_Cascade', 'flush_cache' ) );
add_action( 'created_term', array( 'YDU_Fitment_Cascade', 'flush_cache' ) );
add_action( 'edited_term', array( 'YDU_Fitment_Cascade', 'flush_cache' ) );
add_action( 'delete_term', array( 'YDU_Fitment_Cascade', 'flush_cache' ) );
