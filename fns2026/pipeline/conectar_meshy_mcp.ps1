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
function ClaveValida($k) { return ($k -and $k -match '^msy_[A-Za-z0-9_-]{16,}$') }
$clave = [Environment]::GetEnvironmentVariable("MESHY_API_KEY", "User")
if (-not (ClaveValida $clave)) {
    if ($clave) { Write-Host "   la clave guardada no es válida (se había pegado mal): la reemplazo" -ForegroundColor Red }
    # Se toma del PORTAPAPELES: en el prompt oculto de PowerShell, Ctrl+V no pega el texto,
    # mete un carácter de control (por eso aparecía un solo asterisco y Meshy daba 400).
    Write-Host "   1) En meshy.ai → tu perfil → API, copiá la clave (empieza con msy_)."
    Write-Host "   2) Volvé acá y apretá Enter. No hace falta pegar nada."
    for ($i = 0; $i -lt 3 -and -not (ClaveValida $clave); $i++) {
        Read-Host "   Enter cuando la tengas copiada" | Out-Null
        $clave = -join (("$(Get-Clipboard -Raw)").ToCharArray() | Where-Object { $_ -match '[A-Za-z0-9_-]' })
        if (-not (ClaveValida $clave)) { Write-Host "   lo copiado no parece una clave de Meshy (msy_...). Probá de nuevo." -ForegroundColor Red }
    }
    if (-not (ClaveValida $clave)) { throw "No se pudo leer una clave válida del portapapeles." }
    [Environment]::SetEnvironmentVariable("MESHY_API_KEY", $clave, "User")
    Set-Clipboard -Value " "      # que la clave no quede dando vueltas en el portapapeles
    Write-Host "   guardada ($($clave.Length) caracteres, empieza con $($clave.Substring(0,4)))"
} else {
    Write-Host "   ya está guardada ($($clave.Length) caracteres)"
}
$env:MESHY_API_KEY = $clave
Write-Host "   ok"

Paso "4/4 MCP de Meshy en Claude Code"
# scope user: queda disponible en cualquier carpeta. Si ya estaba, se reemplaza.
# "remove" da error si todavía no existe: en PowerShell 5 con Stop eso corta todo el script
$ErrorActionPreference = "Continue"
cmd /c "claude mcp remove meshy -s user >nul 2>&1"
$ErrorActionPreference = "Stop"
$clave = -join ($clave.ToCharArray() | Where-Object { $_ -match '[A-Za-z0-9_-]' })   # sin comillas ni invisibles
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
