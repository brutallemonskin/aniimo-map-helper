param([string]$Since, [string]$LogonSuffix)
# Read-only, bounded metadata. Never export full event messages, account names,
# paths, security identifiers, machine names or command lines.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$result = [ordered]@{ services = @(); events = @(); errors = @(); event_scan_limit_per_log = 400 }
try {
    $result.session_id = [System.Diagnostics.Process]::GetCurrentProcess().SessionId
    $key = Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Services\CaptureService'
    $result.service_template = @{ start = $key.Start; user_service_flags = $key.UserServiceFlags }
} catch { $result.errors += @{ stage = 'service_template'; hresult = ('0x{0:X8}' -f $_.Exception.HResult) } }
try {
    $services = @(Get-CimInstance Win32_Service -Filter "Name LIKE 'CaptureService%'" -OperationTimeoutSec 5)
    foreach ($service in $services) {
        if ($service.Name -notmatch '^CaptureService(?:_([0-9a-f]+))?$') { continue }
        $suffix = $Matches[1]
        $matchesLogon = $null
        if ($suffix -and $LogonSuffix) { $matchesLogon = ($suffix -ieq $LogonSuffix) }
        $result.services += @{ name = $service.Name; state = $service.State; start_mode = $service.StartMode; matches_current_logon_suffix = $matchesLogon }
    }
    $result.service_context_note = 'Instance suffix compared to current token AuthenticationId; unavailable match stays null. Manual/stopped alone is not evidence of failure.'
} catch { $result.errors += @{ stage = 'services'; hresult = ('0x{0:X8}' -f $_.Exception.HResult) } }
try { $start = [DateTimeOffset]::Parse($Since).LocalDateTime.AddSeconds(-60) }
catch { $start = (Get-Date).AddMinutes(-5) }
foreach ($logName in @('System', 'Application')) {
    try {
        $ids = if ($logName -eq 'System') { @(7000,7001,7023,7024,7031,7034) } else { @(1000,1001,1002) }
        $events = @(Get-WinEvent -FilterHashtable @{ LogName=$logName; Id=$ids; StartTime=$start; EndTime=(Get-Date) } -MaxEvents 400 -ErrorAction Stop)
        if ($events.Count -eq 400) { $result.errors += @{ stage = $logName; note = 'scan_limit_reached' } }
        foreach ($event in $events) {
            if ($result.events.Count -ge 30) { break }
            $xml = [xml]$event.ToXml()
            $raw = ($xml.Event.EventData.Data | ForEach-Object { $_.InnerText }) -join ' '
            if ($raw -notmatch '(?i)CaptureService|Windows\.Graphics\.Capture|windows_capture|ItemProbe\.exe|Fixture\.exe') { continue }
            $modules = @([regex]::Matches($raw, '(?i)[a-z0-9_.-]+\.(?:dll|exe|pyd)\b') | ForEach-Object { $_.Value } | Sort-Object -Unique)
            $codes = @([regex]::Matches($raw, '(?i)\b(?:0x[0-9a-f]{8}|[0-9a-f]{8})\b') | ForEach-Object { $_.Value } | Sort-Object -Unique)
            $result.events += @{ log=$logName; id=$event.Id; time=$event.TimeCreated.ToString('o'); provider=$event.ProviderName; modules=$modules; codes=$codes }
        }
    } catch {
        if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') { continue }
        $result.errors += @{ stage = $logName; hresult = ('0x{0:X8}' -f $_.Exception.HResult); note = 'event_query_unavailable' }
    }
}
$result | ConvertTo-Json -Depth 8 -Compress
