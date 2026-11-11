# Removes the SteamVR stream tag that qos-on.ps1 adds. Needs an elevated PowerShell.
# ('Do not use NLA' is left set: on its own it does nothing.)
Get-NetQosPolicy -Name 'SteamVR stream AF41' -ErrorAction SilentlyContinue | Remove-NetQosPolicy -Confirm:$false
Get-NetQosPolicy | Format-Table Name, AppPathName, DSCPValue -AutoSize
