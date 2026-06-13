/**
 * YDU Fitment finder — cascading Make > Model > Submodel > Variant selector.
 *
 * Built by wp-scripts and enqueued as a script module (no framework). It powers
 * any element carrying `data-ydu-fitment-form` (the theme's header vehicle bar
 * and the [ydu_finder] shortcode), so the theme owns the markup and this module
 * owns the behaviour. Options come from the public fitment/v1 REST endpoints;
 * the selected vehicle persists in localStorage + a cookie and is rendered
 * client-side only, so full-page caching is never fragmented per user.
 *
 * Submitting redirects to the native WooCommerce layered-nav URL
 * (/shop/?filter_make=…&filter_model=…) — identical to the legacy finder.
 */

const cfg = window.yduFitmentConfig || {};
const LEVELS = cfg.levels || [ 'make', 'model', 'submodel', 'variant' ];
const STORAGE_KEY = 'ydu_vehicle';

function readStored() {
	try {
		const raw = window.localStorage.getItem( STORAGE_KEY );
		return raw ? JSON.parse( raw ) : null;
	} catch ( e ) {
		return null;
	}
}

function writeStored( value ) {
	try {
		window.localStorage.setItem( STORAGE_KEY, JSON.stringify( value ) );
	} catch ( e ) {}
	// Mirror to a cookie (1 year) for any server-side consumer; non-essential.
	const maxAge = 60 * 60 * 24 * 365;
	document.cookie = `ydu_vehicle=${ encodeURIComponent( value ? value.map( ( v ) => v.slug ).join( '|' ) : '' ) };path=/;max-age=${ value ? maxAge : 0 };SameSite=Lax`;
}

async function fetchLevel( level, parents ) {
	const route = level === 'make' ? 'makes' : `${ level }s`;
	const url = new URL( `${ cfg.restUrl }/${ route }`, window.location.origin );
	Object.entries( parents ).forEach( ( [ k, v ] ) => url.searchParams.set( k, v ) );
	try {
		const res = await fetch( url.toString(), { headers: { Accept: 'application/json' } } );
		if ( ! res.ok ) {
			return [];
		}
		const data = await res.json();
		return Array.isArray( data ) ? data : [];
	} catch ( e ) {
		return [];
	}
}

function fillSelect( select, placeholder, options ) {
	select.innerHTML = '';
	const ph = document.createElement( 'option' );
	ph.value = '';
	ph.textContent = placeholder;
	select.appendChild( ph );
	options.forEach( ( term ) => {
		const opt = document.createElement( 'option' );
		opt.value = term.slug;
		opt.textContent = term.name;
		select.appendChild( opt );
	} );
	select.disabled = options.length === 0;
}

class Finder {
	constructor( form ) {
		this.form = form;
		this.selects = {};
		LEVELS.forEach( ( level ) => {
			this.selects[ level ] = form.querySelector( `[data-ydu-level="${ level }"]` );
		} );
		this.findBtn = form.querySelector( '[data-ydu-find]' );
		this.resetBtn = form.querySelector( '[data-ydu-reset]' );
		const root = form.closest( '[data-ydu-fitment]' ) || document;
		this.chip = root.querySelector( '[data-ydu-chip]' );
		this.chipText = root.querySelector( '[data-ydu-chip-text]' );

		this.wire();
		this.init();
	}

	placeholder( level ) {
		return level.charAt( 0 ).toUpperCase() + level.slice( 1 );
	}

	parentsFor( level ) {
		const parents = {};
		for ( const l of LEVELS ) {
			if ( l === level ) {
				break;
			}
			const val = this.selects[ l ]?.value;
			if ( val ) {
				parents[ l ] = val;
			}
		}
		return parents;
	}

	async loadLevel( level ) {
		const select = this.selects[ level ];
		if ( ! select ) {
			return;
		}
		const options = await fetchLevel( level, this.parentsFor( level ) );
		fillSelect( select, this.placeholder( level ), options );
	}

	clearFrom( startLevel ) {
		let clearing = false;
		for ( const level of LEVELS ) {
			if ( level === startLevel ) {
				clearing = true;
			}
			if ( clearing && level !== startLevel ) {
				const sel = this.selects[ level ];
				if ( sel ) {
					fillSelect( sel, this.placeholder( level ), [] );
					sel.disabled = true;
				}
			}
		}
	}

	refreshFindState() {
		if ( this.findBtn ) {
			this.findBtn.disabled = ! this.selects.make?.value;
		}
	}

	selectionLabel() {
		return LEVELS.map( ( l ) => {
			const sel = this.selects[ l ];
			if ( ! sel || ! sel.value ) {
				return null;
			}
			return sel.options[ sel.selectedIndex ]?.textContent;
		} ).filter( Boolean ).join( ' ' );
	}

	currentSelection() {
		const sel = [];
		for ( const l of LEVELS ) {
			const node = this.selects[ l ];
			if ( node && node.value ) {
				sel.push( { level: l, slug: node.value, name: node.options[ node.selectedIndex ]?.textContent || node.value } );
			} else {
				break;
			}
		}
		return sel;
	}

	updateChip() {
		if ( ! this.chip || ! this.chipText ) {
			return;
		}
		const label = this.selectionLabel();
		if ( label ) {
			this.chipText.textContent = label;
			this.chip.classList.add( 'set' );
		} else {
			this.chipText.textContent = '—';
			this.chip.classList.remove( 'set' );
		}
	}

	redirect() {
		const filters = cfg.filters || {};
		const url = new URL( cfg.shopUrl, window.location.origin );
		for ( const l of LEVELS ) {
			const sel = this.selects[ l ];
			if ( sel && sel.value && filters[ l ] ) {
				url.searchParams.set( filters[ l ], sel.value );
			}
		}
		window.location.href = url.toString();
	}

	wire() {
		LEVELS.forEach( ( level, idx ) => {
			const select = this.selects[ level ];
			if ( ! select ) {
				return;
			}
			select.addEventListener( 'change', async () => {
				this.clearFrom( level );
				const next = LEVELS[ idx + 1 ];
				if ( select.value && next ) {
					await this.loadLevel( next );
				}
				this.refreshFindState();
				this.persist();
			} );
		} );

		this.form.addEventListener( 'submit', ( e ) => {
			e.preventDefault();
			if ( this.selects.make?.value ) {
				this.redirect();
			}
		} );

		if ( this.resetBtn ) {
			this.resetBtn.addEventListener( 'click', ( e ) => {
				e.preventDefault();
				this.reset();
			} );
		}
	}

	persist() {
		const sel = this.currentSelection();
		writeStored( sel.length ? sel : null );
		this.updateChip();
	}

	reset() {
		LEVELS.forEach( ( level, idx ) => {
			const sel = this.selects[ level ];
			if ( ! sel ) {
				return;
			}
			if ( idx === 0 ) {
				Array.from( sel.options ).forEach( ( o ) => ( o.selected = false ) );
				sel.value = '';
			} else {
				fillSelect( sel, this.placeholder( level ), [] );
				sel.disabled = true;
			}
		} );
		this.refreshFindState();
		writeStored( null );
		this.updateChip();
	}

	async init() {
		await this.loadLevel( LEVELS[ 0 ] );
		const stored = readStored();
		if ( stored && stored.length ) {
			// Re-walk the cascade, selecting each stored level in turn.
			for ( let i = 0; i < stored.length; i++ ) {
				const { level, slug } = stored[ i ];
				const select = this.selects[ level ];
				if ( ! select ) {
					break;
				}
				select.value = slug;
				if ( select.value !== slug ) {
					break; // stored term no longer exists
				}
				const next = LEVELS[ i + 1 ];
				if ( next ) {
					await this.loadLevel( next );
				}
			}
		}
		this.refreshFindState();
		this.updateChip();
	}
}

function boot() {
	document.querySelectorAll( '[data-ydu-fitment-form]' ).forEach( ( form ) => new Finder( form ) );
}

if ( document.readyState === 'loading' ) {
	document.addEventListener( 'DOMContentLoaded', boot );
} else {
	boot();
}
