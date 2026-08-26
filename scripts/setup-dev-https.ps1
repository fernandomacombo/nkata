param(
    [string]$IpAddress = ""
)

$ErrorActionPreference = "Stop"

$repoDir = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $repoDir "frontend"
$certDir = Join-Path $repoDir ".dev-certs"
$certPath = Join-Path $certDir "nkata-dev-cert.pem"
$keyPath = Join-Path $certDir "nkata-dev-key.pem"
$cerPath = Join-Path $certDir "nkata-dev-cert.cer"
$configPath = Join-Path $certDir "openssl-nkata.cnf"
$frontendHttpsEnv = Join-Path $frontendDir ".env.https"

if ([string]::IsNullOrWhiteSpace($IpAddress)) {
    $candidate = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*" -and
            $_.PrefixOrigin -ne "WellKnown"
        } |
        Sort-Object InterfaceMetric, InterfaceIndex |
        Select-Object -First 1

    if (-not $candidate) {
        throw "Nao foi possivel detectar o IPv4 da rede local. Execute novamente com -IpAddress 192.168.x.x"
    }

    $IpAddress = $candidate.IPAddress
}

$parsedIp = $null
if (-not [System.Net.IPAddress]::TryParse($IpAddress, [ref]$parsedIp)) {
    throw "Endereco IPv4 invalido: $IpAddress"
}

function Resolve-OpenSslPath {
    $command = Get-Command openssl.exe -ErrorAction SilentlyContinue
    if ($command) {
        if ($command.PSObject.Properties.Name -contains "Source" -and $command.Source) {
            return $command.Source
        }
        if ($command.FullName) {
            return $command.FullName
        }
    }

    $candidatePaths = New-Object System.Collections.Generic.List[string]

    # Descobre a raiz real do Git instalado, inclusive instalacoes por utilizador
    # como C:\Users\<user>\AppData\Local\Programs\Git\cmd\git.exe.
    $git = Get-Command git.exe -ErrorAction SilentlyContinue
    if ($git) {
        $gitPath = if ($git.PSObject.Properties.Name -contains "Source" -and $git.Source) {
            $git.Source
        } else {
            $git.FullName
        }

        if ($gitPath) {
            $gitCmdDir = Split-Path -Parent $gitPath
            $gitRoot = Split-Path -Parent $gitCmdDir
            $candidatePaths.Add((Join-Path $gitRoot "usr\bin\openssl.exe"))
            $candidatePaths.Add((Join-Path $gitRoot "mingw64\bin\openssl.exe"))
            $candidatePaths.Add((Join-Path $gitRoot "mingw32\bin\openssl.exe"))
        }
    }

    $knownRoots = @(
        (Join-Path $env:ProgramFiles "Git"),
        $(if (${env:ProgramFiles(x86)}) { Join-Path ${env:ProgramFiles(x86)} "Git" } else { $null }),
        $(if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "Programs\Git" } else { $null })
    ) | Where-Object { $_ }

    foreach ($root in $knownRoots) {
        $candidatePaths.Add((Join-Path $root "usr\bin\openssl.exe"))
        $candidatePaths.Add((Join-Path $root "mingw64\bin\openssl.exe"))
        $candidatePaths.Add((Join-Path $root "mingw32\bin\openssl.exe"))
    }

    foreach ($candidatePath in ($candidatePaths | Select-Object -Unique)) {
        if ($candidatePath -and (Test-Path $candidatePath)) {
            return (Get-Item $candidatePath).FullName
        }
    }

    return $null
}

$opensslPath = Resolve-OpenSslPath
if (-not $opensslPath) {
    $gitLocation = (Get-Command git.exe -ErrorAction SilentlyContinue).Source
    if ($gitLocation) {
        throw "OpenSSL nao foi encontrado dentro da instalacao atual do Git ($gitLocation). Atualize o Git for Windows ou instale OpenSSL e tente novamente."
    }
    throw "Git/OpenSSL nao foram encontrados. Instale ou atualize o Git for Windows e tente novamente."
}

Write-Host "OpenSSL encontrado em: $opensslPath" -ForegroundColor DarkGray

New-Item -ItemType Directory -Force -Path $certDir | Out-Null

$opensslConfig = @"
[req]
distinguished_name = dn
x509_extensions = v3_req
prompt = no

[dn]
CN = NKATA Local Development

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
IP.2 = $IpAddress
"@

Set-Content -Path $configPath -Value $opensslConfig -Encoding ascii

& $opensslPath req `
    -x509 `
    -newkey rsa:2048 `
    -sha256 `
    -nodes `
    -days 825 `
    -keyout $keyPath `
    -out $certPath `
    -config $configPath

if ($LASTEXITCODE -ne 0) {
    throw "OpenSSL nao conseguiu gerar o certificado HTTPS."
}

& $opensslPath x509 -in $certPath -outform der -out $cerPath
if ($LASTEXITCODE -ne 0) {
    throw "Nao foi possivel gerar a copia .cer para instalacao no telemovel."
}

try {
    Get-ChildItem Cert:\CurrentUser\Root |
        Where-Object { $_.Subject -eq "CN=NKATA Local Development" } |
        Remove-Item -Force -ErrorAction SilentlyContinue

    Import-Certificate -FilePath $cerPath -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
    $trustedOnWindows = $true
} catch {
    $trustedOnWindows = $false
}

$envContent = @"
# Gerado automaticamente por scripts/setup-dev-https.ps1
# Nao deve ser enviado ao Git.
VITE_API_BASE_URL=https://${IpAddress}:5173
VITE_PUBLIC_APP_ORIGIN=https://${IpAddress}:5173
NKATA_DEV_API_TARGET=http://127.0.0.1:8000
"@
Set-Content -Path $frontendHttpsEnv -Value $envContent -Encoding utf8

Write-Host ""
Write-Host "NKATA HTTPS de desenvolvimento preparado." -ForegroundColor Green
Write-Host "IP local: $IpAddress"
Write-Host "Frontend: https://${IpAddress}:5173"
Write-Host "Certificado para o telemovel: $cerPath"
if ($trustedOnWindows) {
    Write-Host "Certificado confiado no utilizador atual do Windows." -ForegroundColor Green
} else {
    Write-Host "Nao foi possivel adicionar automaticamente o certificado a confianca do Windows." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Proximo comando:"
Write-Host "  cd frontend"
Write-Host "  npm run dev:https"
Write-Host ""
Write-Host "No telemovel, instale nkata-dev-cert.cer como certificado confiavel antes de testar microfone/camara." -ForegroundColor Yellow
