/**
 * Vehicle finder (Year → Make → Model → Submodel → Variant → Engine code).
 * Each dropdown lists only terms that co-occur on products with all selections
 * to its left. The catalog index is fetched once and kept in sessionStorage.
 */

const cfg = window.yduFitmentConfig || {};
const LEVELS = cfg.levels || [ 'year', 'make', 'model', 'submodel', 'variant', 'engine_code' ];
const LABELS = cfg.labels || {};
const STORAGE_KEY = 'ydu_vehicle';
const INDEX_KEY = 'ydu_fit_index_' + ( cfg.cacheVer || 0 );

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
	const maxAge = 60 * 60 * 24 * 365;
	document.cookie = `ydu_vehicle=${ encodeURIComponent( value ? value.map( ( v ) => v.slug ).join( '|' ) : '' ) };path=/;max-age=${ value ? maxAge : 0 };SameSite=Lax`;
}

function levelIndex( level ) {
	return LEVELS.indexOf( level );
}

function ancestorsFor( level, selected ) {
	const idx = levelIndex( level );
	const out = {};
	for ( let i = 0; i < idx; i++ ) {
		const key = LEVELS[ i ];
		if ( selected[ key ] ) {
			out[ key ] = selected[ key ];
		}
	}
	return out;
}

function parentLevel( level ) {
	const idx = levelIndex( level );
	return idx > 0 ? LEVELS[ idx - 1 ] : null;
}

function optionsFor( index, level, selected ) {
	const constraints = ancestorsFor( level, selected );
	const present = new Set();
	for ( const row of index.rows ) {
		let ok = true;
		for ( const [ key, slug ] of Object.entries( constraints ) ) {
			if ( ! ( row[ key ] || [] ).includes( slug ) ) {
				ok = false;
				break;
			}
		}
		if ( ! ok ) {
			continue;
		}
		for ( const slug of row[ level ] || [] ) {
			present.add( slug );
		}
	}
	return ( index.terms[ level ] || [] ).filter( ( term ) => present.has( term.slug ) );
}

function resolve( index, selected ) {
	const clean = {};
	for ( const level of LEVELS ) {
		if ( selected[ level ] ) {
			clean[ level ] = selected[ level ];
		}
	}
	for ( let pass = 0; pass < LEVELS.length; pass++ ) {
		let changed = false;
		for ( const level of LEVELS ) {
			const slugs = optionsFor( index, level, clean ).map( ( term ) => term.slug );
			if ( clean[ level ] && ! slugs.includes( clean[ level ] ) ) {
				delete clean[ level ];
				changed = true;
			}
			if ( slugs.length === 1 && clean[ level ] !== slugs[ 0 ] ) {
				clean[ level ] = slugs[ 0 ];
				changed = true;
			}
		}
		if ( ! changed ) {
			break;
		}
	}
	return clean;
}

function termBySlug( index, level, slug ) {
	return ( index.terms[ level ] || [] ).find( ( term ) => term.slug === slug ) || null;
}

function readCachedIndex() {
	try {
		const cached = window.sessionStorage.getItem( INDEX_KEY );
		if ( ! cached ) {
			return null;
		}
		const data = JSON.parse( cached );
		if ( data && data.terms && data.rows ) {
			return data;
		}
	} catch ( e ) {}
	return null;
}

async function fetchIndex( generation ) {
	const root = String( cfg.restUrl || '' ).replace( /\/$/, '' );
	const res = await fetch( `${ root }/index`, {
		headers: { Accept: 'application/json' },
	} );
	if ( ! res.ok ) {
		throw new Error( 'fitment index unavailable' );
	}
	const data = await res.json();
	if ( generation !== indexFetchGeneration ) {
		return null;
	}
	try {
		window.sessionStorage.setItem( INDEX_KEY, JSON.stringify( data ) );
	} catch ( e ) {}
	return data;
}

let indexFetchGeneration = 0;

async function loadIndex( { preferCache = true } = {} ) {
	if ( preferCache ) {
		const cached = readCachedIndex();
		if ( cached ) {
			return cached;
		}
	}
	const generation = ++indexFetchGeneration;
	return fetchIndex( generation );
}

class Finder {
	constructor( form ) {
		this.form = form;
		this.index = readCachedIndex();
		this.indexGeneration = 0;
		this.selected = {};
		this.fields = {};
		this.skipCommitLevel = null;
		this.findBtn = form.querySelector( '[data-ydu-find]' );
		this.resetBtn = form.querySelector( '[data-ydu-reset]' );
		const root = form.closest( '[data-ydu-fitment]' ) || document;
		this.chip = root.querySelector( '[data-ydu-chip]' );
		this.chipText = root.querySelector( '[data-ydu-chip-text]' );
		LEVELS.forEach( ( level ) => this.upgrade( level ) );
		this.wire();
		this.init();
	}

	upgrade( level ) {
		const select = this.form.querySelector( `[data-ydu-level="${ level }"]` );
		if ( ! select ) {
			return;
		}
		select.hidden = true;
		select.style.display = 'none';
		const combo = document.createElement( 'div' );
		combo.className = 'vb-combo';
		const input = document.createElement( 'input' );
		input.type = 'text';
		input.className = 'vb-search';
		input.placeholder = LABELS[ level ] || select.querySelector( 'option' )?.textContent || level;
		input.setAttribute( 'role', 'combobox' );
		input.setAttribute( 'aria-autocomplete', 'list' );
		input.setAttribute( 'aria-expanded', 'false' );
		input.autocomplete = 'off';
		const menu = document.createElement( 'ul' );
		menu.className = 'vb-menu';
		menu.hidden = true;
		menu.setAttribute( 'role', 'listbox' );
		combo.append( input, menu );
		select.after( combo );
		this.fields[ level ] = { select, input, menu, items: [] };
	}

	wire() {
		LEVELS.forEach( ( level ) => {
			const field = this.fields[ level ];
			if ( ! field ) {
				return;
			}
			field.input.addEventListener( 'focus', () => {
				field.input.select();
				this.open( level );
			} );
			field.input.addEventListener( 'input', () => this.open( level ) );
			field.input.addEventListener( 'keydown', ( event ) => this.onKey( level, event ) );
			field.input.addEventListener( 'blur', () => {
				window.setTimeout( () => this.commitTyped( level ), 120 );
			} );
		} );

		this.form.addEventListener( 'submit', ( event ) => {
			event.preventDefault();
			if ( Object.keys( this.selected ).length ) {
				this.redirect();
			}
		} );
		if ( this.resetBtn ) {
			this.resetBtn.addEventListener( 'click', ( event ) => {
				event.preventDefault();
				this.reset();
			} );
		}
		document.addEventListener( 'click', ( event ) => {
			if ( ! this.form.contains( event.target ) ) {
				this.closeAll();
			}
		} );
	}

	open( level ) {
		const field = this.fields[ level ];
		if ( ! field ) {
			return;
		}
		const parent = parentLevel( level );
		if ( parent && ! this.selected[ parent ] ) {
			field.menu.hidden = true;
			field.items = [];
			field.menu.innerHTML = '';
			field.input.setAttribute( 'aria-expanded', 'false' );
			return;
		}
		if ( ! this.index ) {
			if ( field.items.length ) {
				field.menu.hidden = false;
				field.input.setAttribute( 'aria-expanded', 'true' );
			}
			return;
		}
		this.closeAll( level );
		const chosen = termBySlug( this.index, level, this.selected[ level ] );
		const typed = field.input.value.trim().toLowerCase();
		const query = chosen && typed === chosen.name.toLowerCase() ? '' : typed;
		const options = optionsFor( this.index, level, this.selected ).filter( ( term ) => {
			if ( ! query ) {
				return true;
			}
			return term.name.toLowerCase().includes( query ) || term.slug.toLowerCase().includes( query );
		} );
		field.menu.innerHTML = '';
		field.items = options;
		options.forEach( ( term, index ) => {
			const item = document.createElement( 'li' );
			const button = document.createElement( 'button' );
			button.type = 'button';
			button.textContent = term.name;
			button.setAttribute( 'role', 'option' );
			if ( term.slug === this.selected[ level ] ) {
				button.setAttribute( 'aria-selected', 'true' );
			}
			button.addEventListener( 'mousedown', ( event ) => {
				event.preventDefault();
				this.choose( level, term.slug );
			} );
			item.append( button );
			field.menu.append( item );
			if ( index === 0 ) {
				button.dataset.active = '1';
			}
		} );
		field.menu.hidden = options.length === 0;
		field.input.setAttribute( 'aria-expanded', options.length ? 'true' : 'false' );
	}

	closeAll( except ) {
		LEVELS.forEach( ( level ) => {
			if ( level === except ) {
				return;
			}
			const field = this.fields[ level ];
			if ( ! field ) {
				return;
			}
			field.menu.hidden = true;
			field.input.setAttribute( 'aria-expanded', 'false' );
		} );
	}

	onKey( level, event ) {
		const field = this.fields[ level ];
		const buttons = [ ...field.menu.querySelectorAll( 'button' ) ];
		const current = buttons.findIndex( ( button ) => button.dataset.active === '1' );
		if ( event.key === 'ArrowDown' || event.key === 'ArrowUp' ) {
			event.preventDefault();
			if ( ! buttons.length ) {
				return;
			}
			const next = event.key === 'ArrowDown'
				? ( current + 1 ) % buttons.length
				: ( current - 1 + buttons.length ) % buttons.length;
			buttons.forEach( ( button ) => delete button.dataset.active );
			buttons[ next ].dataset.active = '1';
			buttons[ next ].scrollIntoView( { block: 'nearest' } );
		} else if ( event.key === 'Enter' ) {
			event.preventDefault();
			const active = buttons[ current ] || buttons[ 0 ];
			if ( active ) {
				const term = field.items[ buttons.indexOf( active ) ];
				if ( term ) {
					this.choose( level, term.slug );
				}
			}
		} else if ( event.key === 'Escape' ) {
			this.closeAll();
		}
	}

	commitTyped( level ) {
		if ( this.skipCommitLevel === level ) {
			this.skipCommitLevel = null;
			return;
		}
		const field = this.fields[ level ];
		if ( ! field || ! this.index ) {
			return;
		}
		const typed = field.input.value.trim().toLowerCase();
		this.closeAll();
		if ( ! typed ) {
			if ( this.selected[ level ] ) {
				this.render();
			}
			return;
		}
		const match = optionsFor( this.index, level, this.selected ).find( ( term ) => term.name.toLowerCase() === typed || term.slug.toLowerCase() === typed );
		if ( match ) {
			this.choose( level, match.slug );
			return;
		}
		this.render();
	}

	choose( level, slug ) {
		this.skipCommitLevel = level;
		const idx = levelIndex( level );
		for ( let i = idx + 1; i < LEVELS.length; i++ ) {
			delete this.selected[ LEVELS[ i ] ];
		}
		this.selected[ level ] = slug;
		this.selected = resolve( this.index, this.selected );
		const field = this.fields[ level ];
		const term = termBySlug( this.index, level, this.selected[ level ] );
		if ( field && term ) {
			field.input.value = term.name;
		}
		this.closeAll();
		this.render();
	}

	render() {
		LEVELS.forEach( ( level ) => {
			const field = this.fields[ level ];
			if ( ! field ) {
				return;
			}
			const parent = parentLevel( level );
			const blocked = parent && ! this.selected[ parent ];
			field.input.disabled = Boolean( blocked );
			if ( blocked ) {
				delete this.selected[ level ];
				field.select.value = '';
				field.input.value = '';
				field.items = [];
				field.menu.innerHTML = '';
				field.menu.hidden = true;
				return;
			}
			const term = this.index ? termBySlug( this.index, level, this.selected[ level ] ) : null;
			field.select.value = term ? term.slug : '';
			if ( document.activeElement === field.input ) {
				const typed = field.input.value.trim().toLowerCase();
				if ( term && ( typed === '' || typed === term.name.toLowerCase() || typed === term.slug.toLowerCase() ) ) {
					field.input.value = term.name;
				}
			} else {
				field.input.value = term ? term.name : '';
			}
		} );
		if ( this.findBtn ) {
			this.findBtn.disabled = ! Object.keys( this.selected ).length;
		}
		this.persist();
	}

	selectionList() {
		if ( ! this.index ) {
			return [];
		}
		return LEVELS.filter( ( level ) => this.selected[ level ] ).map( ( level ) => {
			const term = termBySlug( this.index, level, this.selected[ level ] );
			return { level, slug: this.selected[ level ], name: term ? term.name : this.selected[ level ] };
		} );
	}

	updateChip() {
		if ( ! this.chip || ! this.chipText ) {
			return;
		}
		const label = this.selectionList().map( ( item ) => item.name ).join( ' ' );
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
		const url = new URL( cfg.shopUrl || '/shop/', window.location.origin );
		for ( const level of LEVELS ) {
			if ( this.selected[ level ] && filters[ level ] ) {
				url.searchParams.set( filters[ level ], this.selected[ level ] );
			}
		}
		window.location.href = url.toString();
	}

	persist() {
		const list = this.selectionList();
		writeStored( list.length ? list : null );
		this.updateChip();
	}

	reset() {
		this.selected = {};
		this.closeAll();
		this.render();
	}

	applyStoredSelection() {
		if ( ! this.index ) {
			return;
		}
		const stored = readStored();
		if ( stored && stored.length ) {
			const selected = {};
			stored.forEach( ( item ) => {
				if ( item && item.level && item.slug ) {
					selected[ item.level ] = item.slug;
				}
			} );
			this.selected = resolve( this.index, selected );
		} else if ( ! Object.keys( this.selected ).length ) {
			this.selected = resolve( this.index, {} );
		} else {
			this.selected = resolve( this.index, this.selected );
		}
		this.render();
	}

	async init() {
		const generation = ++this.indexGeneration;
		if ( this.index ) {
			this.applyStoredSelection();
			const refreshGen = ++indexFetchGeneration;
			fetchIndex( refreshGen )
				.then( ( fresh ) => {
					if ( ! fresh || generation !== this.indexGeneration ) {
						return;
					}
					this.index = fresh;
					this.applyStoredSelection();
				} )
				.catch( () => {} );
			return;
		}
		try {
			this.index = await loadIndex( { preferCache: true } );
			if ( generation !== this.indexGeneration || ! this.index ) {
				return;
			}
			this.applyStoredSelection();
		} catch ( e ) {
			return;
		}
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
