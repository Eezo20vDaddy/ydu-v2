<?php
/**
 * Convert one image to PNG under 7 MB using GD.
 * CLI only. Paths must stay inside the seeded data directory.
 *
 * Usage: php studio-png.php <src> <dest>
 */

if ( PHP_SAPI !== 'cli' ) {
	fwrite( STDERR, "cli only\n" );
	exit( 1 );
}

$src  = $argv[1] ?? '';
$dest = $argv[2] ?? '';
$root = '/var/www/html/wp-content/ydu-seed/data/studio-media';

$real_root = realpath( $root );
$real_src  = realpath( $src );
if ( ! $real_root || ! $real_src || ! str_starts_with( $real_src, $real_root ) ) {
	fwrite( STDERR, "source outside studio media\n" );
	exit( 1 );
}
$dest_dir = realpath( dirname( $dest ) );
if ( ! $dest_dir || ! str_starts_with( $dest_dir, $real_root ) ) {
	fwrite( STDERR, "dest outside studio media\n" );
	exit( 1 );
}

$info = getimagesize( $real_src );
if ( ! $info ) {
	fwrite( STDERR, "unreadable image\n" );
	exit( 1 );
}
$img = match ( $info[2] ) {
	IMAGETYPE_JPEG => imagecreatefromjpeg( $real_src ),
	IMAGETYPE_PNG => imagecreatefrompng( $real_src ),
	IMAGETYPE_WEBP => function_exists( 'imagecreatefromwebp' ) ? imagecreatefromwebp( $real_src ) : false,
	IMAGETYPE_GIF => imagecreatefromgif( $real_src ),
	IMAGETYPE_BMP => function_exists( 'imagecreatefrombmp' ) ? imagecreatefrombmp( $real_src ) : false,
	default => false,
};
if ( ! $img ) {
	fwrite( STDERR, "unsupported image\n" );
	exit( 1 );
}

$cap = 7 * 1024 * 1024;
$w   = imagesx( $img );
$h   = imagesy( $img );
do {
	imagepng( $img, $dest, 6 );
	$bytes = filesize( $dest );
	if ( $bytes !== false && $bytes <= $cap ) {
		echo (int) $bytes;
		exit( 0 );
	}
	$w = max( 1, (int) ( $w * 0.85 ) );
	$h = max( 1, (int) ( $h * 0.85 ) );
	$next = imagecreatetruecolor( $w, $h );
	imagecopyresampled( $next, $img, 0, 0, 0, 0, $w, $h, imagesx( $img ), imagesy( $img ) );
	imagedestroy( $img );
	$img = $next;
} while ( $w > 32 && $h > 32 );

fwrite( STDERR, "could not fit under 7MB\n" );
exit( 1 );
