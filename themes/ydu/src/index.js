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

document.addEventListener( 'DOMContentLoaded', () => {
	initDrawer();
	initCopyButtons();
} );
