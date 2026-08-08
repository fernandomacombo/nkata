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
        throw "Não foi possível detectar o IPv4 da rede local. Execute novamente com -IpAddress 192.168.x.x"
    }

    $IpAddress = $candidate.IPAddress
}

$parsedIp = $null
if (-not [System.Net.IPAddress]::TryParse($IpAddress, [ref]$parsedIp)) {
    throw "Endereço IPv4 inválido: $IpAddress"
}

$openssl = Get-Command openssl.exe -ErrorAction SilentlyContinue
if (-not $openssl) {
    $candidates = @(
        (Join-Path $env:ProgramFiles "Git\usr\bin\openssl.exe"),
        (Join-Path $env:ProgramFiles "Git\mingw64\bin\openssl.exe")
    )

    foreach ($candidatePath in $candidates) {
        if (Test-Path $candidatePath) {
            $openssl = Get-Item $candidatePath
            break
        }
    }
}

if (-not $openssl) {
    throw "OpenSSL não foi encontrado. Instale/atualize o Git for Windows ou coloque openssl.exe no PATH."
}

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

& $openssl.Source req `
    -x509 `
    -newkey rsa:2048 `
    -sha256 `
    -nodes `
    -days 825 `
    -keyout $keyPath `
    -out $certPath `
    -config $configPath

if ($LASTEXITCODE -ne 0) {
    throw "OpenSSL não conseguiu gerar o certificado HTTPS."
}

& $openssl.Source x509 -in $certPath -outform der -out $cerPath
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível gerar a cópia .cer para instalação no telemóvel."
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
# Não deve ser enviado ao Git.
VITE_API_BASE_URL=https://${IpAddress}:5173
NKATA_DEV_API_TARGET=http://127.0.0.1:8000
"@
Set-Content -Path $frontendHttpsEnv -Value $envContent -Encoding utf8

Write-Host ""
Write-Host "NKATA HTTPS de desenvolvimento preparado." -ForegroundColor Green
Write-Host "IP local: $IpAddress"
Write-Host "Frontend: https://${IpAddress}:5173"
Write-Host "Certificado para o telemóvel: $cerPath"
if ($trustedOnWindows) {
    Write-Host "Certificado confiado no utilizador atual do Windows." -ForegroundColor Green
} else {
    Write-Host "Não foi possível adicionar automaticamente o certificado à confiança do Windows." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Próximo comando:"
Write-Host "  cd frontend"
Write-Host "  npm run dev:https"
Write-Host ""
Write-Host "No telemóvel, instale nkata-dev-cert.cer como certificado confiável antes de testar microfone/câmara." -ForegroundColor Yellow
