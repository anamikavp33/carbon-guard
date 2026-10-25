# Creates the Android project files for the Carbon Guard app and adds the permissions it needs.
# Run once, from the mobile_app folder, in PowerShell:
#     powershell -ExecutionPolicy Bypass -File setup_android.ps1
# Safe to run again: existing files (lib/, test/, pubspec.yaml) are never overwritten and
# permissions are only added if they are missing.
param([string]$Manifest = "android\app\src\main\AndroidManifest.xml", [switch]$ManifestOnly)

$ErrorActionPreference = "Stop"

if (-not $ManifestOnly) {
    if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) {
        Write-Error "Flutter is not installed or not on PATH. See SETUP_GUIDE.md, section 'Mobile app'."
    }
    # Generates android/ (and other missing files) without touching existing Dart code.
    flutter create --platforms=android --project-name carbon_guard_app --org com.carbonguard .
    flutter pub get
}

if (-not (Test-Path $Manifest)) { Write-Error "Cannot find $Manifest" }
$xml = Get-Content $Manifest -Raw

$permissions = @(
    "android.permission.INTERNET",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION"
)
foreach ($p in $permissions) {
    if ($xml -notmatch [regex]::Escape("android:name=""$p""")) {
        # Insert right after the opening <manifest ...> tag.
        $xml = [regex]::Replace($xml, "(<manifest[^>]*>)", "`$1`r`n    <uses-permission android:name=""$p"" />", 1)
        Write-Host "Added permission $p"
    }
}

# The development backend uses plain http://, which Android blocks unless this is allowed.
# Remove it (and use https) for a real deployment.
if ($xml -notmatch "usesCleartextTraffic") {
    $xml = [regex]::Replace($xml, "<application", "<application`r`n        android:usesCleartextTraffic=""true""", 1)
    Write-Host "Allowed http:// traffic for the development backend"
}
$xml = $xml -replace 'android:label="carbon_guard_app"', 'android:label="Carbon Guard"'

# Write UTF-8 without a byte-order mark (Windows PowerShell's "utf8" would add one).
[System.IO.File]::WriteAllText((Resolve-Path $Manifest).Path, $xml, (New-Object System.Text.UTF8Encoding $false))
Write-Host "Android setup complete. Next: flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000"
