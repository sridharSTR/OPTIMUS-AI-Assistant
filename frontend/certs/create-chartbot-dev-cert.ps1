$ErrorActionPreference = "Stop"

$certDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pfxPath = Join-Path $certDir "chartbot-dev.pfx"
$cerPath = Join-Path $certDir "chartbot-dev.cer"
$crtPath = Join-Path $certDir "chartbot-dev.crt"
$password = "chartbot-dev"

$rsa = [System.Security.Cryptography.RSA]::Create(2048)
$subject = "CN=chartbot-dev"
$request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
  $subject,
  $rsa,
  [System.Security.Cryptography.HashAlgorithmName]::SHA256,
  [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
)

$sanBuilder = [System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
$sanBuilder.AddDnsName("localhost")
$sanBuilder.AddDnsName("chartbot-dev")
$sanBuilder.AddIpAddress([System.Net.IPAddress]::Parse("127.0.0.1"))
$sanBuilder.AddIpAddress([System.Net.IPAddress]::Parse("::1"))
$sanBuilder.AddIpAddress([System.Net.IPAddress]::Parse("192.168.0.5"))
$sanBuilder.AddIpAddress([System.Net.IPAddress]::Parse("10.37.54.193"))

$request.CertificateExtensions.Add($sanBuilder.Build())
$request.CertificateExtensions.Add(
  [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $true)
)
$request.CertificateExtensions.Add(
  [System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new(
    [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature -bor
    [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyEncipherment,
    $true
  )
)
$request.CertificateExtensions.Add(
  [System.Security.Cryptography.X509Certificates.X509SubjectKeyIdentifierExtension]::new($request.PublicKey, $false)
)

$serverAuthOid = [System.Security.Cryptography.Oid]::new("1.3.6.1.5.5.7.3.1")
$enhancedKeyUsages = [System.Security.Cryptography.OidCollection]::new()
[void]$enhancedKeyUsages.Add($serverAuthOid)
$request.CertificateExtensions.Add(
  [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($enhancedKeyUsages, $true)
)

$notBefore = [System.DateTimeOffset]::Now.AddDays(-1)
$notAfter = $notBefore.AddYears(2)
$certificate = $request.CreateSelfSigned($notBefore, $notAfter)
$certificate = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
  $certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Pfx, $password),
  $password,
  [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable -bor
  [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet
)

[System.IO.File]::WriteAllBytes($pfxPath, $certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Pfx, $password))
[System.IO.File]::WriteAllBytes($cerPath, $certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))

$base64 = [System.Convert]::ToBase64String($certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert), [System.Base64FormattingOptions]::InsertLineBreaks)
$pem = "-----BEGIN CERTIFICATE-----`r`n$base64`r`n-----END CERTIFICATE-----`r`n"
[System.IO.File]::WriteAllText($crtPath, $pem)

Write-Host "Created $pfxPath"
Write-Host "Created $cerPath"
Write-Host "Created $crtPath"
