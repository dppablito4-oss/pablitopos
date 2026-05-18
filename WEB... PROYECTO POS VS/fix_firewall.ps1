$prog = "python.exe"
$ruleName = "PablitoPOS Dev Access"
$port = 8000

# Verificar si somos admin
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Solicitando permisos de administrador para arreglar el firewall..." -ForegroundColor Yellow
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "--- ARREGLANDO PERMISOS DE RED ---" -ForegroundColor Cyan

# 1. Eliminar reglas viejas si existen para limpiar
Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

# 2. Crear la regla que permite TODO el tráfico entrante al puerto 8000 (TCP)
New-NetFirewallRule -DisplayName $ruleName `
                    -Direction Inbound `
                    -LocalPort $port `
                    -Protocol TCP `
                    -Action Allow `
                    -Profile Any

Write-Host "✅ LISTO. El puerto $port ha sido desbloqueado." -ForegroundColor Green
Write-Host "Presiona Enter para salir..."
Read-Host
