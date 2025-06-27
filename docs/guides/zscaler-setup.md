# Setting up ViolentUTF with Zscaler

If you're behind a corporate proxy using Zscaler, you'll need to add your certificates to the Docker build process.

## Steps to Add Zscaler Certificates

1. **Export your Zscaler certificates** from your system:
   
   **On macOS:**
   ```bash
   # Export from Keychain
   security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > zscaler.pem
   security find-certificate -a -p /Library/Keychains/System.keychain | grep -A 20 -B 5 "Zscaler" > zscaler.crt
   ```

   **On Windows:**
   - Open Certificate Manager (certmgr.msc)
   - Navigate to Trusted Root Certification Authorities
   - Find Zscaler certificates
   - Export as Base-64 encoded X.509 (.CER)
   - Rename to zscaler.crt

2. **Copy certificates to the FastAPI directory:**
   ```bash
   cp zscaler.crt violentutf_api/fastapi_app/
   cp zscaler.pem violentutf_api/fastapi_app/
   # If you have a CA.crt file:
   cp CA.crt violentutf_api/fastapi_app/
   ```

3. **Run the setup script:**
   ```bash
   ./setup_macos.sh
   ```

## Alternative: Disable Garak Temporarily

If you continue to have SSL issues, you can temporarily disable garak:

```bash
# Edit requirements.txt and comment out garak
sed -i '' 's/^garak/# garak/' violentutf_api/fastapi_app/requirements.txt

# Run setup
./setup_macos.sh
```

## Docker Build Behind Proxy

If you need to set proxy environment variables for Docker builds:

```bash
# Set proxy for Docker daemon (add to ~/.docker/config.json)
{
  "proxies": {
    "default": {
      "httpProxy": "http://your-proxy:8080",
      "httpsProxy": "http://your-proxy:8080",
      "noProxy": "localhost,127.0.0.1"
    }
  }
}
```

Or build with proxy arguments:
```bash
docker build \
  --build-arg http_proxy=http://your-proxy:8080 \
  --build-arg https_proxy=http://your-proxy:8080 \
  --build-arg no_proxy=localhost,127.0.0.1 \
  -t your-image .
```

## Notes

- The Dockerfile now automatically handles Zscaler certificates if present
- Certificates are optional - the build will continue if they're not found
- The Rust installation will retry with SSL verification disabled if initial attempt fails
- This approach maintains security while working in corporate environments