@echo off
:: Script para abrir el puerto 8000 en el Firewall de Windows
:: Este script debe ser ejecutado como Administrador (por el instalador)

echo Configurando Firewall para PablitoPOS...

netsh advfirewall firewall delete rule name="PablitoPOS Dev Access" >nul 2>&1
netsh advfirewall firewall add rule name="PablitoPOS Dev Access" dir=in action=allow protocol=TCP localport=8000 profile=any

if %errorlevel% equ 0 (
    echo [EXITO] Regla de firewall creada correctamente.
) else (
    echo [ERROR] No se pudo crear la regla. Asegurese de ejecutar como Administrador.
)
