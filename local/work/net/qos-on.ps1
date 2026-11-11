# Tags SteamVR's stream to the Frame (vrserver.exe, UDP) as AF41 (DSCP 34) so a router with WMM
# sends it in Wi-Fi's video queue, ahead of ordinary traffic. Needs an elevated PowerShell.
# Undo with qos-off.ps1.
$ErrorActionPreference = 'Stop'
$name = 'SteamVR stream AF41'

# Windows applies DSCP from local QoS policies on a PC that is not on a domain only with this set.
$key = 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\QoS'
if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
New-ItemProperty -Path $key -Name 'Do not use NLA' -Value '1' -PropertyType String -Force | Out-Null

Get-NetQosPolicy -Name $name -ErrorAction SilentlyContinue | Remove-NetQosPolicy -Confirm:$false
New-NetQosPolicy -Name $name -AppPathNameMatchCondition 'vrserver.exe' -IPProtocolMatchCondition UDP `
    -DSCPAction 34 -NetworkProfile All | Out-Null
Get-NetQosPolicy -Name $name | Format-List Name, AppPathName, IPProtocol, DSCPValue, NetworkProfile
