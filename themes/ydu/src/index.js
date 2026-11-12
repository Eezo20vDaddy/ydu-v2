/**
 * YDU theme front-end interactions: mobile drawer (open/close, focus trap,
 * ESC, backdrop) and promo "copy code" buttons.
 *
 * The vehicle finder cascade is NOT here — it lives in the ydu-fitment plugin
 * (it owns the data, endpoints, persistence and redirect). This file only
 * covers theme-presentation behaviour.
 */

import './style.scss';

function initDrawer() {
	const hamburger = document.getElementById( 'yduHamburger' );
	const drawer = document.getElementById( 'yduDrawer' );
	const backdrop = document.getElementById( 'yduDrawerBackdrop' );
	const closeBtn = document.getElementById( 'yduDrawerClose' );
	if ( ! hamburger || ! drawer || ! backdrop || ! closeBtn ) {
		return;
	}
	let lastFocused = null;

	const open = () => {
		lastFocused = document.activeElement;
		drawer.hidden = false;
		backdrop.hidden = false;
		requestAnimationFrame( () =>
			requestAnimationFrame( () => {
				drawer.classList.add( 'open' );
				backdrop.classList.add( 'open' );
			} )
		);
		hamburger.setAttribute( 'aria-expanded', 'true' );
		document.body.style.overflow = 'hidden';
		closeBtn.focus();
	};

	const close = () => {
		drawer.classList.remove( 'open' );
		backdrop.classList.remove( 'open' );
		hamburger.setAttribute( 'aria-expanded', 'false' );
		document.body.style.overflow = '';
		window.setTimeout( () => {
			drawer.hidden = true;
			backdrop.hidden = true;
		}, 240 );
		if ( lastFocused ) {
			lastFocused.focus();
		}
	};

	hamburger.addEventListener( 'click', open );
	closeBtn.addEventListener( 'click', close );
	backdrop.addEventListener( 'click', close );
	drawer.querySelectorAll( 'nav a' ).forEach( ( a ) => a.addEventListener( 'click', close ) );
	document.addEventListener( 'keydown', ( e ) => {
		if ( e.key === 'Escape' && ! drawer.hidden ) {
			close();
		}
	} );

	drawer.addEventListener( 'keydown', ( e ) => {
		if ( e.key !== 'Tab' ) {
			return;
		}
		const focusables = drawer.querySelectorAll( 'a[href], button' );
		if ( ! focusables.length ) {
			return;
		}
		const first = focusables[ 0 ];
		const last = focusables[ focusables.length - 1 ];
		if ( e.shiftKey && document.activeElement === first ) {
			e.preventDefault();
			last.focus();
		} else if ( ! e.shiftKey && document.activeElement === last ) {
			e.preventDefault();
			first.focus();
		}
	} );
}

function initProductCardGalleries() {
	const reducedMotion = window.matchMedia( '(prefers-reduced-motion: reduce)' ).matches;

	document.querySelectorAll( '.product-card' ).forEach( ( card ) => {
		const gallery = card.querySelector( '.pc-gallery' );
		if ( ! gallery ) {
			return;
		}

		const slides = gallery.querySelectorAll( '.pc-gallery__slide' );
		if ( slides.length < 2 || reducedMotion ) {
			return;
		}

		const intervalMs = Number.parseInt(
			gallery.getAttribute( 'data-pc-interval' ) || '5000',
			10
		);
		let index = 0;
		let timer = null;

		const show = ( nextIndex ) => {
			slides.forEach( ( slide, i ) => {
				slide.classList.toggle( 'is-active', i === nextIndex );
			} );
			index = nextIndex;
		};

		const advance = () => {
			show( ( index + 1 ) % slides.length );
		};

		const start = () => {
			stop();
			timer = window.setInterval( advance, intervalMs );
		};

		const stop = () => {
			if ( timer !== null ) {
				window.clearInterval( timer );
				timer = null;
			}
		};

		start();
		card.addEventListener( 'mouseenter', stop );
		card.addEventListener( 'mouseleave', start );
		card.addEventListener( 'focusin', stop );
		card.addEventListener( 'focusout', ( event ) => {
			if ( ! card.contains( event.relatedTarget ) ) {
				start();
			}
		} );
	} );
}

function initCopyButtons() {
	document.querySelectorAll( '[data-ydu-copy]' ).forEach( ( btn ) => {
		btn.addEventListener( 'click', () => {
			const code = ( btn.getAttribute( 'data-ydu-copy' ) || '' ).trim();
			const restore = () => {
				btn.classList.add( 'copied' );
				const original = btn.textContent;
				btn.textContent = 'Copied!';
				window.setTimeout( () => {
					btn.classList.remove( 'copied' );
					btn.textContent = original;
				}, 1800 );
			};
			if ( navigator.clipboard?.writeText ) {
				navigator.clipboard.writeText( code ).then( restore, restore );
			} else {
				restore();
			}
		} );
	} );
}

const LIST_KEYS = { wishlist: 'ydu_wishlist', compare: 'ydu_compare' };

function readList( list ) {
	try {
		const raw = window.localStorage.getItem( LIST_KEYS[ list ] );
		const parsed = raw ? JSON.parse( raw ) : [];
		return Array.isArray( parsed ) ? parsed.map( ( id ) => Number( id ) ).filter( ( id ) => id > 0 ) : [];
	} catch ( err ) {
		return [];
	}
}

function writeList( list, ids ) {
	window.localStorage.setItem( LIST_KEYS[ list ], JSON.stringify( ids ) );
}

function applyListUi() {
	const counts = { wishlist: readList( 'wishlist' ), compare: readList( 'compare' ) };
	Object.keys( counts ).forEach( ( list ) => {
		const ids = counts[ list ];
		document.querySelectorAll( `[data-ydu-count="${ list }"]` ).forEach( ( badge ) => {
			badge.textContent = String( ids.length );
			badge.hidden = ids.length === 0;
		} );
		document.querySelectorAll( `[data-ydu-count-link="${ list }"]` ).forEach( ( link ) => {
			const label = list === 'wishlist' ? 'Saved parts' : 'Compare';
			link.setAttribute( 'aria-label', `${ label }, ${ ids.length } items` );
		} );
		document.querySelectorAll( `[data-ydu-list="${ list }"]` ).forEach( ( button ) => {
			const on = ids.includes( Number( button.getAttribute( 'data-product-id' ) ) );
			button.classList.toggle( 'is-on', on );
			button.setAttribute( 'aria-pressed', on ? 'true' : 'false' );
		} );
	} );
}

let persistChain = Promise.resolve();

function persistLists() {
	const config = window.yduLists;
	if ( ! config?.loggedIn || ! config.root || ! config.nonce ) {
		return;
	}
	// One save at a time, always reading the latest lists, so a slow save
	// cannot overwrite a newer one.
	persistChain = persistChain
		.catch( () => {} )
		.then( () => window.fetch( config.root, {
			method: 'POST',
			credentials: 'same-origin',
			headers: {
				'Content-Type': 'application/json',
				'X-WP-Nonce': config.nonce,
			},
			body: JSON.stringify( {
				wishlist: readList( 'wishlist' ),
				compare: readList( 'compare' ),
			} ),
		} ) );
}

function decodeText( value ) {
	const box = document.createElement( 'textarea' );
	box.innerHTML = value || '';
	return box.value;
}

async function hydrateListsFromAccount() {
	const config = window.yduLists;
	if ( ! config?.loggedIn || ! config.root || ! config.nonce ) {
		return;
	}
	try {
		const response = await window.fetch( config.root, {
			credentials: 'same-origin',
			headers: { 'X-WP-Nonce': config.nonce },
		} );
		if ( ! response.ok ) {
			return;
		}
		const data = await response.json();
		let changed = false;
		[ 'wishlist', 'compare' ].forEach( ( list ) => {
			const local = readList( list );
			const remote = Array.isArray( data[ list ] ) ? data[ list ].map( Number ) : [];
			const max = list === 'compare' ? ( config.compareMax || 4 ) : ( config.wishlistMax || 100 );
			const merged = Array.from( new Set( [ ...remote, ...local ] ) ).slice( 0, max );
			if ( merged.join() !== local.join() ) {
				writeList( list, merged );
				changed = true;
			}
		} );
		if ( changed ) {
			persistLists();
		}
	} catch ( err ) {
		// The browser copy still works if the account copy cannot be read.
	}
}

function toggleList( list, productId ) {
	const config = window.yduLists || {};
	const ids = readList( list );
	const index = ids.indexOf( productId );
	if ( index >= 0 ) {
		ids.splice( index, 1 );
	} else {
		const max = list === 'compare' ? ( config.compareMax || 4 ) : ( config.wishlistMax || 100 );
		if ( ids.length >= max ) {
			window.alert( list === 'compare' ? config.compareFull : config.wishlistFull );
			return;
		}
		ids.push( productId );
	}
	writeList( list, ids );
	applyListUi();
	persistLists();
}

function money( product ) {
	const prices = product.prices;
	if ( ! prices || prices.price == null || prices.price === '' ) {
		return '';
	}
	const minor = Number( prices.currency_minor_unit ?? 2 );
	const raw = Number( prices.price ) / ( 10 ** minor );
	const dec = prices.currency_decimal_separator || '.';
	const thou = prices.currency_thousand_separator || ',';
	const [ whole, frac = '' ] = raw.toFixed( minor ).split( '.' );
	const grouped = whole.replace( /\B(?=(\d{3})+(?!\d))/g, thou );
	const amount = minor > 0 ? grouped + dec + frac : grouped;
	const decode = ( html ) => {
		const box = document.createElement( 'textarea' );
		box.innerHTML = html || '';
		return box.value;
	};
	return `${ decode( prices.currency_prefix ) }${ amount }${ decode( prices.currency_suffix ) }`;
}

function stockLabel( product ) {
	return product.is_in_stock ? 'In stock' : 'Backorder';
}

function renderSavedPage() {
	const root = document.getElementById( 'yduSaved' );
	const config = window.yduLists;
	if ( ! root || ! config?.store ) {
		return;
	}
	const list = root.getAttribute( 'data-ydu-screen' );
	const ids = readList( list );
	const empty = root.querySelector( '[data-ydu-saved-empty]' );
	const status = root.querySelector( '[data-ydu-saved-status]' );
	const holder = root.querySelector( '[data-ydu-saved-list]' );
	if ( ! ids.length ) {
		if ( empty ) {
			empty.hidden = false;
		}
		return;
	}
	if ( empty ) {
		empty.hidden = true;
	}
	if ( status ) {
		status.hidden = false;
		status.textContent = 'Loading parts…';
	}
	const url = `${ config.store }?include=${ ids.join( ',' ) }&per_page=${ Math.max( ids.length, 1 ) }`;
	window.fetch( url )
		.then( ( response ) => response.json() )
		.then( ( products ) => {
			if ( status ) {
				status.hidden = true;
			}
			if ( ! Array.isArray( products ) || ! holder ) {
				return;
			}
			const byId = new Map( products.map( ( product ) => [ product.id, product ] ) );
			holder.replaceChildren();
			const table = document.createElement( list === 'compare' ? 'table' : 'div' );
			table.className = list === 'compare' ? 'ydu-compare' : 'ydu-wishlist';
			if ( list === 'compare' ) {
				const head = document.createElement( 'tr' );
				[ 'Part', 'SKU', 'Price', 'Stock', '' ].forEach( ( label ) => {
					const cell = document.createElement( 'th' );
					cell.textContent = label;
					head.appendChild( cell );
				} );
				const thead = document.createElement( 'thead' );
				thead.appendChild( head );
				table.appendChild( thead );
				const body = document.createElement( 'tbody' );
				ids.forEach( ( id ) => {
					const product = byId.get( id );
					if ( ! product ) {
						return;
					}
					const row = document.createElement( 'tr' );
					const name = document.createElement( 'td' );
					const link = document.createElement( 'a' );
					link.href = product.permalink;
					link.textContent = decodeText( product.name );
					name.appendChild( link );
					const sku = document.createElement( 'td' );
					sku.textContent = product.sku || '—';
					const price = document.createElement( 'td' );
					price.textContent = money( product );
					const stock = document.createElement( 'td' );
					stock.textContent = stockLabel( product );
					const actions = document.createElement( 'td' );
					actions.appendChild( cartLink( product ) );
					actions.appendChild( removeButton( list, id ) );
					row.append( name, sku, price, stock, actions );
					body.appendChild( row );
				} );
				table.appendChild( body );
			} else {
				ids.forEach( ( id ) => {
					const product = byId.get( id );
					if ( ! product ) {
						return;
					}
					const row = document.createElement( 'article' );
					row.className = 'ydu-wish-row';
					const link = document.createElement( 'a' );
					link.href = product.permalink;
					link.textContent = decodeText( product.name );
					const sku = document.createElement( 'span' );
					sku.className = 'ydu-wish-sku';
					sku.textContent = product.sku || '';
					const price = document.createElement( 'span' );
					price.className = 'ydu-wish-price';
					price.textContent = money( product );
					const actions = document.createElement( 'div' );
					actions.className = 'ydu-wish-actions';
					actions.appendChild( cartLink( product ) );
					actions.appendChild( removeButton( list, id ) );
					row.append( link, sku, price, actions );
					table.appendChild( row );
				} );
			}
			holder.appendChild( table );
		} )
		.catch( () => {
			if ( status ) {
				status.hidden = false;
				status.textContent = 'Could not load these parts. Refresh the page.';
			}
		} );
}

function cartLink( product ) {
	const link = document.createElement( 'a' );
	link.className = 'btn-cart';
	link.href = product.add_to_cart?.url || product.permalink;
	link.textContent = 'Add to cart';
	return link;
}

function removeButton( list, id ) {
	const button = document.createElement( 'button' );
	button.type = 'button';
	button.className = 'ydu-remove';
	button.textContent = 'Remove';
	button.addEventListener( 'click', () => {
		toggleList( list, id );
		renderSavedPage();
	} );
	return button;
}

function openQuickView( productId ) {
	const dialog = document.getElementById( 'yduQuickView' );
	const body = dialog?.querySelector( '[data-ydu-quick-body]' );
	const config = window.yduLists;
	if ( ! dialog || ! body || ! config?.store ) {
		return;
	}
	body.textContent = 'Loading…';
	if ( typeof dialog.showModal === 'function' && ! dialog.open ) {
		dialog.showModal();
	}
	window.fetch( `${ config.store }/${ productId }` )
		.then( ( response ) => response.json() )
		.then( ( product ) => {
			body.replaceChildren();
			const title = document.createElement( 'h2' );
			title.id = 'yduQuickTitle';
			title.textContent = decodeText( product.name ) || 'Part';
			const sku = document.createElement( 'p' );
			sku.className = 'ydu-quick__sku';
			sku.textContent = product.sku ? `Part no. ${ product.sku }` : '';
			const price = document.createElement( 'p' );
			price.className = 'ydu-quick__price';
			price.textContent = money( product );
			const stock = document.createElement( 'p' );
			stock.textContent = stockLabel( product );
			const excerpt = document.createElement( 'p' );
			excerpt.className = 'ydu-quick__excerpt';
			excerpt.textContent = ( product.short_description || '' ).replace( /<[^>]+>/g, '' );
			const actions = document.createElement( 'div' );
			actions.className = 'ydu-quick__actions';
			actions.appendChild( cartLink( product ) );
			const full = document.createElement( 'a' );
			full.className = 'ydu-quick__full';
			full.href = product.permalink || '#';
			full.textContent = 'Full details';
			actions.appendChild( full );
			if ( product.images?.[ 0 ]?.src ) {
				const image = document.createElement( 'img' );
				image.src = product.images[ 0 ].src;
				image.alt = decodeText( product.images[ 0 ].alt || product.name || '' );
				body.append( image, title, sku, price, stock, excerpt, actions );
			} else {
				body.append( title, sku, price, stock, excerpt, actions );
			}
		} )
		.catch( () => {
			body.textContent = 'Could not load this part.';
		} );
}

function initLists() {
	const dialog = document.getElementById( 'yduQuickView' );
	document.addEventListener( 'click', ( event ) => {
		const listButton = event.target.closest( '[data-ydu-list]' );
		if ( listButton ) {
			event.preventDefault();
			toggleList( listButton.getAttribute( 'data-ydu-list' ), Number( listButton.getAttribute( 'data-product-id' ) ) );
			return;
		}
		const quickButton = event.target.closest( '[data-ydu-quick]' );
		if ( quickButton ) {
			event.preventDefault();
			openQuickView( Number( quickButton.getAttribute( 'data-ydu-quick' ) ) );
			return;
		}
		if ( event.target.closest( '[data-ydu-quick-close]' ) && dialog?.open ) {
			dialog.close();
		}
	} );
	hydrateListsFromAccount().finally( () => {
		applyListUi();
		renderSavedPage();
	} );
}

document.addEventListener( 'DOMContentLoaded', () => {
	initDrawer();
	initProductCardGalleries();
	initCopyButtons();
	initLists();
} );
