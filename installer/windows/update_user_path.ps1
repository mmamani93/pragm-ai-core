[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Add", "Remove")]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$Directory
)

$ErrorActionPreference = "Stop"

function Get-NormalizedPath([string]$Value) {
    $expanded = [Environment]::ExpandEnvironmentVariables($Value)
    try {
        return [IO.Path]::GetFullPath($expanded).TrimEnd("\")
    }
    catch {
        return $expanded.TrimEnd("\")
    }
}

$current = [Environment]::GetEnvironmentVariable("Path", "User")
$entries = if ([string]::IsNullOrWhiteSpace($current)) {
    @()
}
else {
    @($current.Split(";") | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}
$target = Get-NormalizedPath $Directory
$matching = @($entries | Where-Object { (Get-NormalizedPath $_) -ieq $target })

if ($Action -eq "Add") {
    if ($matching.Count -eq 0) {
        $separator = if ([string]::IsNullOrEmpty($current) -or $current.EndsWith(";")) { "" } else { ";" }
        [Environment]::SetEnvironmentVariable("Path", "$current$separator$Directory", "User")
        exit 10
    }
    exit 0
}

$comparison = [StringComparison]::OrdinalIgnoreCase
if ([string]::Equals($current, $Directory, $comparison)) {
    [Environment]::SetEnvironmentVariable("Path", $null, "User")
    exit 0
}
$appended = ";$Directory"
if ($current.EndsWith($appended, $comparison)) {
    [Environment]::SetEnvironmentVariable(
        "Path", $current.Substring(0, $current.Length - $appended.Length), "User"
    )
    exit 0
}

$remaining = @($entries | Where-Object { (Get-NormalizedPath $_) -ine $target })
if ($remaining.Count -ne $entries.Count) {
    $updated = if ($remaining.Count -eq 0) { $null } else { $remaining -join ";" }
    [Environment]::SetEnvironmentVariable("Path", $updated, "User")
}
exit 0
