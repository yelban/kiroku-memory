# macOS Code Signing and Notarization Guide

This guide documents the complete process for setting up macOS code signing and notarization for Kiroku Memory Desktop App.

## Prerequisites

- Apple Developer Program membership ($99/year)
- macOS for generating certificates
- GitHub repository with Actions enabled

## Step 1: Generate Certificate Signing Request (CSR)

### Open Keychain Access

```bash
open -a "Keychain Access"
```

### Create CSR

1. Menu → **Keychain Access** → **Certificate Assistant** → **Request a Certificate From a Certificate Authority...**
2. Fill in:
   - **User Email Address**: Your email
   - **Common Name**: Your name
   - **CA Email Address**: Leave empty
   - Select **Saved to disk**
3. Save the `.certSigningRequest` file

## Step 2: Create Developer ID Certificate

### Apple Developer Portal

1. Go to https://developer.apple.com/account/resources/certificates/list
2. Click **+** (blue plus button)
3. Under **Software**, select **Developer ID Application**
   > This is for distributing apps outside the App Store
4. Click **Continue**
5. Upload the `.certSigningRequest` file from Step 1
6. Click **Continue** → **Download**

### Install Certificate

Double-click the downloaded `.cer` file to install it to Keychain, or:

```bash
security import ~/Downloads/developerID_application.cer -k ~/Library/Keychains/login.keychain-db
```

### Verify Installation

```bash
security find-identity -v -p codesigning
```

You should see:
```
1) ABC123... "Developer ID Application: Your Name (TEAMID)"
   1 valid identities found
```

Note your **Team ID** (the code in parentheses, e.g., `TXU8UPLYJP`).

## Step 3: Export Certificate as .p12

1. Open **Keychain Access**
2. Click **My Certificates** in the sidebar
3. Find **Developer ID Application: Your Name**
4. Expand it (click the arrow) to confirm it has a private key
5. **Right-click** → **Export...**
6. Format: **.p12**
7. Set a strong password (remember this!)
8. Save to Desktop

### Convert to Base64

```bash
base64 -i ~/Desktop/Certificates.p12 | pbcopy
```

The Base64 content is now in your clipboard.

## Step 4: Create App-Specific Password

Apple requires an app-specific password for notarization.

1. Go to https://appleid.apple.com/account/manage
2. Sign in
3. **App-Specific Passwords** → **Generate password**
4. Name it `GitHub Actions`
5. Save the generated password (format: `xxxx-xxxx-xxxx-xxxx`)

## Step 5: Configure GitHub Secrets

Go to your repository: `Settings` → `Secrets and variables` → `Actions`

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `APPLE_CERTIFICATE` | Base64-encoded .p12 certificate |
| `APPLE_CERTIFICATE_PASSWORD` | Password you set when exporting .p12 |
| `APPLE_ID` | Your Apple ID email |
| `APPLE_PASSWORD` | App-specific password from Step 4 |
| `APPLE_TEAM_ID` | Your Team ID (e.g., `TXU8UPLYJP`) |

## Step 6: Configure GitHub Actions Workflow

### Import Certificate

Add this step to import the certificate into the CI keychain:

```yaml
- name: Import Apple certificate
  if: matrix.platform == 'darwin'
  env:
    APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE }}
    APPLE_CERTIFICATE_PASSWORD: ${{ secrets.APPLE_CERTIFICATE_PASSWORD }}
  run: |
    # Create temporary keychain
    KEYCHAIN_PATH=$RUNNER_TEMP/app-signing.keychain-db
    KEYCHAIN_PASSWORD=$(openssl rand -base64 32)

    # Decode certificate
    echo -n "$APPLE_CERTIFICATE" | base64 --decode -o $RUNNER_TEMP/certificate.p12

    # Create and configure keychain
    security create-keychain -p "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH
    security set-keychain-settings -lut 21600 $KEYCHAIN_PATH
    security unlock-keychain -p "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH

    # Import certificate
    security import $RUNNER_TEMP/certificate.p12 -P "$APPLE_CERTIFICATE_PASSWORD" -A -t cert -f pkcs12 -k $KEYCHAIN_PATH
    security set-key-partition-list -S apple-tool:,apple: -s -k "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH
    security list-keychain -d user -s $KEYCHAIN_PATH

    # Verify certificate
    security find-identity -v -p codesigning $KEYCHAIN_PATH
```

### Sign Embedded Binaries (Important!)

If your app bundles native binaries (e.g., Python with `.so`/`.dylib` files), you must sign them **before** the Tauri build:

```yaml
- name: Sign Python bundle binaries
  if: matrix.platform == 'darwin'
  env:
    APPLE_SIGNING_IDENTITY: "Developer ID Application: Your Name (TEAMID)"
  run: |
    PYTHON_BUNDLE="tools/packaging/dist/current/python"

    # Sign all .so files
    find "$PYTHON_BUNDLE" -name "*.so" -type f | while read -r file; do
      codesign --force --options runtime --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$file"
    done

    # Sign all .dylib files
    find "$PYTHON_BUNDLE" -name "*.dylib" -type f | while read -r file; do
      codesign --force --options runtime --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$file"
    done

    # Sign executables
    if [ -f "$PYTHON_BUNDLE/bin/python3.11" ]; then
      codesign --force --options runtime --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$PYTHON_BUNDLE/bin/python3.11"
    fi
```

### Build with Signing and Notarization

```yaml
- name: Build Tauri app (macOS with signing)
  if: matrix.platform == 'darwin'
  working-directory: desktop
  env:
    APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE }}
    APPLE_CERTIFICATE_PASSWORD: ${{ secrets.APPLE_CERTIFICATE_PASSWORD }}
    APPLE_SIGNING_IDENTITY: "Developer ID Application: Your Name (TEAMID)"
    APPLE_ID: ${{ secrets.APPLE_ID }}
    APPLE_PASSWORD: ${{ secrets.APPLE_PASSWORD }}
    APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
  run: npm run tauri build -- --target ${{ matrix.target }}
```

## Step 7: Configure Tauri

In `tauri.conf.json`, configure macOS signing:

```json
{
  "bundle": {
    "macOS": {
      "minimumSystemVersion": "10.15",
      "signingIdentity": "-",
      "providerShortName": "YOUR_TEAM_ID",
      "infoPlist": "Info.plist"
    }
  }
}
```

- `signingIdentity: "-"` tells Tauri to use the `APPLE_SIGNING_IDENTITY` environment variable
- `providerShortName` is your Team ID

## Troubleshooting

### "The binary is not signed with a valid Developer ID certificate"

**Cause**: Embedded binaries (like Python `.so` files) are not signed.

**Solution**: Sign all `.so`, `.dylib`, and executable files before Tauri build. See Step 6.

### "The signature does not include a secure timestamp"

**Cause**: Missing `--timestamp` flag when signing.

**Solution**: Always use `codesign --timestamp` when signing.

### Certificate not found in CI

**Cause**: Keychain not properly configured.

**Solution**: Ensure you:
1. Create a new keychain
2. Unlock it
3. Import the certificate
4. Set partition list
5. Add to keychain search list

### Notarization timeout

**Cause**: Apple's notarization service can be slow.

**Solution**: Notarization typically takes 1-5 minutes. If it times out, the app may still be notarized - check Apple's notarization history.

## Verification

After successful notarization, users can install the app without:
- Running `xattr -cr`
- Right-clicking to open
- Seeing "app is damaged" warnings

To verify an app is properly signed and notarized:

```bash
# Check signature
codesign -dv --verbose=4 "Kiroku Memory.app"

# Check notarization
spctl -a -v "Kiroku Memory.app"
```

## References

- [Apple: Notarizing macOS Software Before Distribution](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Tauri: Code Signing](https://v2.tauri.app/distribute/sign/macos/)
- [Resolving Common Notarization Issues](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution/resolving_common_notarization_issues)
