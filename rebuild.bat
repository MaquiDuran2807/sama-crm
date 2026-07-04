@echo off
title SAMA AdTech -- Rebuild & Restart
chcp 65001 >nul

echo ============================================
echo  SAMA AdTech -- Rebuild Docker Image
echo ============================================
echo.

:: 1. Detener servicios si estan corriendo
echo [1/4] Deteniendo servicios en ejecucion...
docker compose down --remove-orphans 2>nul
if %errorlevel% neq 0 (
    echo      [WARN] No hay servicios activos que detener.
) else (
    echo      [OK] Servicios detenidos.
)
echo.

:: 2. Rebuild de la imagen
echo [2/4] Reconstruyendo imagen Docker...
docker build -t sama-adtech:latest .
if %errorlevel% neq 0 (
    echo      [ERROR] Fallo la construccion de la imagen.
    pause
    exit /b 1
)
echo      [OK] Imagen reconstruida: sama-adtech:latest
echo.

:: 3. Iniciar servicios
echo [3/4] Iniciando servicios (modo desarrollo)...
docker compose up -d
if %errorlevel% neq 0 (
    echo      [ERROR] Fallo al iniciar servicios.
    pause
    exit /b 1
)
echo      [OK] Servicios iniciados.
echo.

:: 4. Estado final
echo [4/4] Estado de los servicios:
echo.
docker compose ps
echo.
echo ============================================
echo  Listo. Acceder en: http://localhost:8000
echo  Logs: docker compose logs -f
echo ============================================
echo.
