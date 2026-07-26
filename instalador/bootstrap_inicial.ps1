# Baixador de componentes para o instalador bootstrap (Etapa 6 do plano v4).
#
# Espelho "bare machine" do `instalador/baixar_componentes.py`. Mesmo
# comportamento: confere hash local, baixa de GitHub Releases com sha256,
# extrai em <raiz>/ferramentas/<componente>/. Idempotente.
#
# Quando usar:
#   * Em máquina do usuário final sem Python (instalador bootstrap).
#   * Em CI / release engineering.
#   * Em `iniciar_v4.bat` como fallback do buscador em Python.
#
# Nenhuma dependência externa: PowerShell 5.1+ (que vem com Windows 10/11)
# já tem Invoke-WebRequest, Expand-Archive e Get-FileHash.

[CmdletBinding()]
param(
    [string]$Tag          = 'v4.0.0',
    [string]$Destino      = '',
    [string[]]$Componentes,
    [string[]]$Skip,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

# Resolve destino default: a raiz do projeto (pai da pasta instalador/).
if ([string]::IsNullOrWhiteSpace($Destino)) {
    $Destino = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}
if ($null -eq $Componentes) { $Componentes = @() }
if ($null -eq $Skip)        { $Skip = @('cuda', 'modelos-diarizacao') }

$REPO = 'jpneto106/Transkript.ai'

function Asset-Nome($componente, $tag) {
    "Transkript.ai-${tag}-${componente}.zip"
}

function Asset-Url($tag, $asset) {
    "https://github.com/$REPO/releases/download/$tag/$asset"
}

function Asset-Url-Sha($tag, $asset) {
    "https://github.com/$REPO/releases/download/$tag/${asset}.sha256"
}

function Get-HashLocal($caminho) {
    if (-not (Test-Path -LiteralPath $caminho)) { return $null }
    return (Get-FileHash -LiteralPath $caminho -Algorithm SHA256).Hash.ToLower()
}

function Componente-Precisa($destino, $componente, $tag) {
    $asset = Asset-Nome $componente $tag
    $alvo  = Join-Path (Join-Path $destino 'ferramentas') $componente
    $tem   = (Test-Path -LiteralPath $alvo) -and `
             (@(Get-ChildItem -LiteralPath $alvo -Recurse -Force -ErrorAction SilentlyContinue).Count -gt 0)
    $hashEsperado = $null
    try {
        $resp = Invoke-WebRequest -Uri (Asset-Url-Sha $tag $asset) -UseBasicParsing -ErrorAction Stop
        $hashEsperado = ($resp.Content.Trim() -split '\s+')[0].ToLower()
    } catch {
        $hashEsperado = $null
    }

    if ($hashEsperado -and $tem -and -not $Force) {
        # Confere um arquivo-marcador. Se o componente já extraiu e bateu
        # o hash gravado em cache, não baixa de novo.
        $pCache  = Join-Path (Join-Path $destino 'dados') '_cache'
        $cache   = Join-Path $pCache "${componente}.sha256"
        if ((Test-Path -LiteralPath $cache) -and `
            ((Get-Content -LiteralPath $cache -Raw -Encoding UTF8).Trim().ToLower() -eq $hashEsperado)) {
            return [pscustomobject]@{ Precisa = $false; Hash = $hashEsperado }
        }
    }

    if (-not $hashEsperado) {
        return [pscustomobject]@{ Precisa = (-not $tem); Hash = $null }
    }
    return [pscustomobject]@{ Precisa = $true; Hash = $hashEsperado }
}

function Baixar-Com-Progresso($url, $destinoArquivo) {
    $req = [System.Net.HttpWebRequest]::Create($url)
    $req.UserAgent = 'Transkript.ai-bootstrap'
    $resp = $req.GetResponse()
    $total = [int64]$resp.ContentLength
    $stream = $resp.GetResponseStream()

    $fs = [System.IO.File]::Create($destinoArquivo)
    $buf = New-Object byte[] (64KB)
    $lidos = 0L
    while (($n = $stream.Read($buf, 0, $buf.Length)) -gt 0) {
        $fs.Write($buf, 0, $n)
        $lidos += $n
        if ($total -gt 0) {
            $pct = 100 * $lidos / $total
            Write-Progress -Activity "Baixando" -Status $url.Split('/')[-1] `
                -PercentComplete ([int]$pct)
        }
    }
    $fs.Close(); $stream.Close(); $resp.Close()
    Write-Progress -Activity "Baixando" -Completed
}

function Extrair-Zip($zip, $destino) {
    if (-not (Test-Path -LiteralPath $destino)) {
        New-Item -ItemType Directory -Path $destino -Force | Out-Null
    }
    $zipFull = (Resolve-Path -LiteralPath $zip).Path
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zipFull, $destino)
}

function Tem-Nvidia {
    # Heurística simples: a DLL nvcuda.dll existe nas pastas de driver da NVIDIA.
    # Mais sofisticado do que isso não compensa: NVIDIA-SMI pode não estar no PATH
    # em máquinas com o driver instalado silenciosamente.
    $candidatos = @(
        "$env:ProgramFiles\NVIDIA Corporation\NVSMI\nvml.dll",
        "$env:ProgramFiles\NVIDIA GPU Computing Toolkit\CUDA\nvml.dll",
        "$env:WINDIR\System32\nvml.dll"
    )
    foreach ($c in $candidatos) { if (Test-Path -LiteralPath $c) { return $true } }
    return $false
}

function Diarizacao-Ativa($destino) {
    $p1 = Join-Path $destino 'dados'
    $cfg = Join-Path $p1 'configuracoes.json'
    if (-not (Test-Path -LiteralPath $cfg)) { return $false }
    try {
        $obj = Get-Content -LiteralPath $cfg -Raw -Encoding UTF8 | ConvertFrom-Json
        return [bool]$obj.diarizar
    } catch {
        return $false
    }
}

function Processar-Componente($destino, $componente, $tag) {
    $info = Componente-Precisa $destino $componente $tag
    if (-not $info.Precisa) { return "  ${componente}: ja presente, hash confere, pulando" }
    if (-not $info.Hash)    { return "  ${componente}: asset nao encontrado no Release ${tag}" }
    if ($DryRun)             { return "  ${componente}: baixaria" }

    Write-Host "  ${componente}: baixando de ${tag}..."
    $cacheDir = Join-Path (Join-Path $destino 'dados') '_cache'
    if (-not (Test-Path -LiteralPath $cacheDir)) {
        New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
    }
    $zip = Join-Path $cacheDir "${componente}.zip"
    $url = Asset-Url $tag (Asset-Nome $componente $tag)
    try {
        Baixar-Com-Progresso $url $zip
    } catch {
        Remove-Item -LiteralPath $zip -ErrorAction SilentlyContinue
        return "  ${componente}: ERRO no download: $_"
    }

    $calc = Get-HashLocal $zip
    if ($calc -ne $info.Hash.ToLower()) {
        Remove-Item -LiteralPath $zip -ErrorAction SilentlyContinue
        throw "sha256 nao bateu em ${componente}: esperado $($info.Hash), calculado $calc"
    }

    $alvo = Join-Path (Join-Path $destino 'ferramentas') $componente
    Extrair-Zip $zip $alvo
    Set-Content -LiteralPath (Join-Path $cacheDir "${componente}.sha256") `
                 -Value $info.Hash -Encoding UTF8 -NoNewline
    $mb = [math]::Round((Get-Item -LiteralPath $zip).Length / 1MB, 1)
    return "  ${componente}: OK ($mb MB)"
}

# ---------- corpo principal ----------

Write-Host "Destino: $Destino"
Write-Host "Tag:     $Tag"

$desejados = @('casca', 'servidor', 'frontend', 'ffmpeg')
if (Tem-Nvidia)         { $desejados += 'cuda' }
if (Diarizacao-Ativa $Destino) { $desejados += 'modelos-diarizacao' }

if ($Componentes.Count -gt 0) { $desejados = $desejados | Where-Object { $Componentes -contains $_ } }
foreach ($s in $Skip)          { $desejados = $desejados | Where-Object { $_ -ne $s } }

Write-Host "Componentes: $($desejados -join ', ')"
Write-Host ""

foreach ($c in $desejados) {
    try {
        $msg = Processar-Componente $Destino $c $Tag
    } catch {
        Write-Host "  ${c}: ERRO: $_"
        continue
    }
    Write-Host $msg
}

Write-Host ""
Write-Host "Pronto."
