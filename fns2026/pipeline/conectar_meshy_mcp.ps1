# FNS 2026 · conecta el MCP oficial de Meshy (@meshy-ai/meshy-mcp-server) a Claude Code en esta PC
# y abre Claude en el proyecto. Usa la clave MESHY_API_KEY que ya guardó instalar_windows.ps1
# (no hay que escribirla de nuevo). Requiere plan Pro de Meshy.
#
#   irm https://raw.githubusercontent.com/facundo-20/Ciudades/claude/fiesta-sol-2026-immersive-ph9915/fns2026/pipeline/conectar_meshy_mcp.ps1 | iex

$ErrorActionPreference = "Stop"
function Paso($t) { Write-Host "`n== $t" -ForegroundColor Yellow }
function RefrescarPath {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                (Join-Path $HOME ".local\bin")
}

Paso "1/4 Node.js (el MCP de Meshy corre con npx)"
if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    winget install --id OpenJS.NodeJS.LTS -e --silent --accept-source-agreements --accept-package-agreements | Out-Host
    RefrescarPath
} else { Write-Host "   ya está" }

Paso "2/4 Claude Code"
RefrescarPath
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    irm https://claude.ai/install.ps1 | iex
    RefrescarPath
} else { Write-Host "   ya está" }

Paso "3/4 Clave de Meshy"
$clave = [Environment]::GetEnvironmentVariable("MESHY_API_KEY", "User")
if (-not $clave) {
    $seg = Read-Host "   Pegá la clave de Meshy (no se ve)" -AsSecureString
    $clave = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seg))
    [Environment]::SetEnvironmentVariable("MESHY_API_KEY", $clave, "User")
}
$env:MESHY_API_KEY = $clave
Write-Host "   ok"

Paso "4/4 MCP de Meshy en Claude Code"
# scope user: queda disponible en cualquier carpeta. Si ya estaba, se reemplaza.
claude mcp remove meshy -s user 2>$null | Out-Null
claude mcp add meshy -s user -e "MESHY_API_KEY=$clave" -- npx -y "@meshy-ai/meshy-mcp-server"
claude mcp list

$proyecto = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Ciudades"
Write-Host "`nListo. Abro Claude Code en $proyecto." -ForegroundColor Green
Write-Host "Primera orden sugerida:" -ForegroundColor Green
Write-Host '  Leé fns2026/ARQUITECTURA.md y fns2026/pipeline/lista_modelos.json. Con el MCP de Meshy generá el_hongo,'
Write-Host '  bochas, suelo_arcilla y barranca_colorada fotorrealistas, bajalos a fns2026/modelos_meshy/<nombre>/ y'
Write-Host '  pasalos por fns2026/pipeline/correr_todo.py. Mostrame las vistas previas.'
Set-Location $proyecto
claude
