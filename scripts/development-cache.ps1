param(
    [Parameter(Mandatory = $true)][string]$CacheRoot,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$repository = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\')
if ($CacheRoot -notmatch '^[A-Za-z]:[\\/]') {
    throw 'CacheRoot must be an absolute path outside the source drive.'
}
$cache = [IO.Path]::GetFullPath($CacheRoot).TrimEnd('\')
if ($cache.Length -le 3 -or $cache.StartsWith('\\')) {
    throw 'CacheRoot must be a local directory, not a drive root or UNC share.'
}
if ([IO.Path]::GetPathRoot($cache) -ieq [IO.Path]::GetPathRoot($repository)) {
    throw 'CacheRoot must be on a different drive from the source checkout.'
}
# Reject existing links in the destination chain before creating anything.
$cursor = $cache
while ($cursor.Length -gt 3) {
    if (Test-Path -LiteralPath $cursor) {
        if ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'CacheRoot cannot traverse a junction or symbolic link.'
        }
    }
    $cursor = Split-Path -Parent $cursor
}
$settings = [ordered]@{
    DM_CACHE_ROOT = $cache
    PIP_CACHE_DIR = Join-Path $cache 'python\pip'
    POETRY_CACHE_DIR = Join-Path $cache 'python\poetry'
    POETRY_VIRTUALENVS_PATH = Join-Path $cache 'python\venvs'
    POETRY_VIRTUALENVS_IN_PROJECT = 'false'
    PYTHONPYCACHEPREFIX = Join-Path $cache 'python\pycache\pysus'
    MYPY_CACHE_DIR = Join-Path $cache 'python\mypy\pysus'
    PRE_COMMIT_HOME = Join-Path $cache 'pre-commit\pysus'
    PYSUS_CACHEPATH = Join-Path $cache 'python\data\pysus'
    TEMP = Join-Path $cache 'temp\pysus'
    TMP = Join-Path $cache 'temp\pysus'
}
if (-not $DryRun) {
    foreach ($entry in $settings.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
    }
    New-Item -ItemType Directory -Path $settings.TEMP -Force | Out-Null
}
$settings
