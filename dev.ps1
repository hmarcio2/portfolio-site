<#
.SYNOPSIS
  Sobe o chat (API) e o site para desenvolvimento local, cada um numa janela minimizada.

.DESCRIPTION
  Gera o site (build.py) e sobe a API do chat em http://localhost:8000 e o site em http://localhost:8080 (abre o navegador).
  Aceita também a página aberta direto do disco (file://), que o navegador envia com Origin "null":
  por isso o CORS da API recebe "null" aqui. NÃO use isso em produção.

  Chaves: o app lê um .env em 00-site-chat/ ou na raiz do workspace (ignorado pelo git). Sem chave,
  o chat responde em modo offline (echo). Para reaproveitar a GOOGLE_API_KEY de outro projeto sem copiá-la:

    .\dev.ps1 -KeyFrom C:\Users\Marcio\Documents\python\Chatbot\.env

  Para encerrar: feche as duas janelas minimizadas (ou use -Stop).

.EXAMPLE
  .\dev.ps1
  .\dev.ps1 -KeyFrom C:\caminho\outro\.env
  .\dev.ps1 -Stop
#>
param(
    [int]$ApiPort = 8000,
    [int]$SitePort = 8080,
    [string]$KeyFrom,
    [switch]$NoBrowser,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"

if ($Stop) {
    # Acha os processos por LINHA DE COMANDO, não pela porta (netstat e Get-NetTCPConnection não enxergam todos os
    # listeners em alguns ambientes). Só encerra o que começa com o python.exe do venv deste workspace e roda o
    # uvicorn do chat ou o http.server do site; no Windows o venv é um lançador, então há um processo pai e um filho.
    $ours = Get-CimInstance Win32_Process | Where-Object {
        $_.ProcessId -ne $PID -and $_.CommandLine -and
        ($_.CommandLine.StartsWith("`"$py`" ") -or $_.CommandLine.StartsWith("$py ")) -and
        ($_.CommandLine -match "-m uvicorn app\.main:create_app.*--port $ApiPort\b" -or $_.CommandLine -match "-m http\.server $SitePort\b")
    }
    if (-not $ours) { "nada para encerrar (API na porta $ApiPort e site na porta $SitePort não encontrados)"; return }
    foreach ($p in $ours) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        "encerrado: pid $($p.ProcessId)  $($p.CommandLine.Replace($py, 'python'))"
    }
    return
}

if (-not (Test-Path $py)) {
    throw "Não achei $py. Crie o venv: python -m venv .venv; .venv\Scripts\python -m pip install -e `"_core[langchain,dev]`" -r 00-site-chat\requirements.txt"
}

# Chave de outro .env: só a GOOGLE_API_KEY, só na memória deste processo (nada é copiado para o disco).
if ($KeyFrom) {
    $line = Select-String -Path $KeyFrom -Pattern '^\s*GOOGLE_API_KEY\s*=\s*(.+?)\s*$' | Select-Object -First 1
    if (-not $line) { throw "GOOGLE_API_KEY não encontrada em $KeyFrom" }
    $env:GOOGLE_API_KEY = $line.Matches[0].Groups[1].Value.Trim('"', "'")
}

$hasKey = [bool]$env:GOOGLE_API_KEY -or (Test-Path (Join-Path $root ".env")) -or (Test-Path (Join-Path $root "00-site-chat\.env"))
if (-not $hasKey) { Write-Warning "Nenhuma chave encontrada: o chat vai responder em modo offline (echo). Use -KeyFrom ou crie um .env." }

# CORS: o site em localhost:<porta> e a página aberta de file:// ("null")
$env:PORTFOLIO_ALLOWED_ORIGINS = "http://localhost:$SitePort,http://127.0.0.1:$SitePort,null"
$env:PORTFOLIO_RATE_LIMIT_PER_MINUTE = "30"

Start-Process -FilePath $py -WorkingDirectory (Join-Path $root "00-site-chat") -WindowStyle Minimized `
    -ArgumentList "-m", "uvicorn", "app.main:create_app", "--factory", "--port", $ApiPort
# O site é gerado de content/ + templates/ para dist/; rode `python build.py` de novo depois de editar um texto.
& $py (Join-Path $root "build.py")
if ($LASTEXITCODE -ne 0) { throw "O site não foi gerado: corrija o conteúdo indicado acima." }
Start-Process -FilePath $py -WorkingDirectory $root -WindowStyle Minimized `
    -ArgumentList "-m", "http.server", $SitePort, "--directory", (Join-Path $root "dist")

for ($i = 0; $i -lt 40; $i++) {
    try { $h = Invoke-RestMethod "http://localhost:$ApiPort/health" -TimeoutSec 2; break } catch { Start-Sleep -Milliseconds 500 }
}
if ($h) { "API no ar: $($h.provider), $($h.chunks) trechos de conhecimento" } else { Write-Warning "A API não respondeu em 20 s; veja a janela minimizada." }
"Site: http://localhost:$SitePort/"
if (-not $NoBrowser) { Start-Process "http://localhost:$SitePort/" }
