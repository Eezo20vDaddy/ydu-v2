# Build clean, installable zips for the ydu theme and ydu-fitment plugin.
# Excludes dev-only files. Output: dist/ydu.zip, dist/ydu-fitment.zip
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$dist = Join-Path $root 'dist'
Remove-Item $dist -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $dist | Out-Null

$stage = Join-Path $env:TEMP 'ydu-pkg'
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $stage | Out-Null

Write-Host '==> Staging theme'
robocopy (Join-Path $root 'themes\ydu') (Join-Path $stage 'ydu') /E /XD node_modules src /XF .gitignore package.json package-lock.json *.map /NFL /NDL /NJH /NJS /NP | Out-Null

Write-Host '==> Staging plugin'
robocopy (Join-Path $root 'plugins\ydu-fitment') (Join-Path $stage 'ydu-fitment') /E /XD node_modules src tests vendor /XF package.json package-lock.json composer.json composer.lock phpunit.xml.dist *.map /NFL /NDL /NJH /NJS /NP | Out-Null

Write-Host '==> Compressing'
Compress-Archive -Path (Join-Path $stage 'ydu') -DestinationPath (Join-Path $dist 'ydu.zip') -Force
Compress-Archive -Path (Join-Path $stage 'ydu-fitment') -DestinationPath (Join-Path $dist 'ydu-fitment.zip') -Force
Remove-Item $stage -Recurse -Force

Get-ChildItem $dist | Select-Object Name, @{n='KB';e={[math]::Round($_.Length/1KB,1)}} | Format-Table -AutoSize
