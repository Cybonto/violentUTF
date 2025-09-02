# Self-Signed Certificate Preparation for ViolentUTF Keycloak (Local Development)

This guide outlines the steps to generate a self-signed SSL/TLS certificate for Keycloak to enable HTTPS in a local Docker development environment. This certificate will be configured to be valid for:
- `localhost`: For accessing Keycloak directly from your host machine's browser.
- `keycloak`: The service name used by other Docker containers (e.g., `violentutf_app`) to communicate with Keycloak over the Docker network.

**Prerequisites:**
* OpenSSL installed on your system. (Usually available by default on macOS and Linux. Windows users might need to install it, e.g., via Git Bash or WSL).

**Steps:**

1.  **Create a Directory for Certificates:**
    It's good practice to keep your certificate files organized. If you don't have one already, create a `certs` directory within your `ViolentUTF_nightly` project folder:
    ```bash
    mkdir -p ViolentUTF_nightly/certs
    cd ViolentUTF_nightly/certs
    ```
    *(Adjust the path `ViolentUTF_nightly/certs` if your project root is different or if you prefer another location. Ensure your `docker-compose.yml` volume mounts point to the correct location.)*

2.  **Create an OpenSSL Configuration File (`openssl.cnf`):**
    Inside the `certs` directory, create a file named `openssl.cnf` with the following content. This file defines the parameters for your certificate, including the crucial Subject Alternative Names (SANs).

    ```ini
    # ViolentUTF_nightly/certs/openssl.cnf
    [req]
    default_bits       = 2048
    prompt             = no
    default_md         = sha256
    distinguished_name = dn
    req_extensions     = v3_req # Ensure this line is present

    [dn]
    C=US # Country
    ST=North Carolina # State or Province
    L=Raleigh # Locality (City)
    O=ViolentUTF Development # Organization
    OU=Development Team # Organizational Unit
    CN=localhost # Common Name (can be localhost or your primary dev domain)

    [v3_req] # Ensure this section matches the req_extensions
    subjectAltName = @alt_names

    [alt_names]
    DNS.1 = localhost   # For browser access from host machine
    DNS.2 = keycloak    # For service-to-service communication within Docker network
    # Optional: Add IP addresses if needed, though hostnames are generally preferred
    # IP.1 = 127.0.0.1
    ```
    * Adjust the `C`, `ST`, `L`, `O`, `OU` values as you see fit.
    * The `CN` (Common Name) is set to `localhost`.
    * The `[alt_names]` section with `DNS.1 = localhost` and `DNS.2 = keycloak` is critical for avoiding hostname mismatch errors.

3.  **Generate the Private Key (`key.pem`):**
    In your terminal (still inside the `certs` directory), run the following command to generate a 2048-bit RSA private key:
    ```bash
    openssl genrsa -out key.pem 2048
    ```
    This will create a file named `key.pem`.

4.  **Generate a Certificate Signing Request (`csr.pem`):**
    Using the private key and the configuration file, create a CSR:
    ```bash
    openssl req -new -key key.pem -out csr.pem -config openssl.cnf
    ```
    This will create `csr.pem`.

5.  **Generate the Self-Signed Certificate (`cert.pem`):**
    Now, sign the CSR with your private key to generate the self-signed certificate. This certificate will be valid for 365 days (you can adjust the `-days` parameter). The `-extensions v3_req` and `-extfile openssl.cnf` flags ensure the Subject Alternative Names are included from your configuration file.
    ```bash
    openssl x509 -req -days 365 -in csr.pem -signkey key.pem -out cert.pem -extensions v3_req -extfile openssl.cnf
    ```
    This creates `cert.pem`.

6.  **Verify the Certificate (Optional but Recommended):**
    You can inspect the generated certificate to ensure it contains the correct Subject Alternative Names:
    ```bash
    openssl x509 -in cert.pem -noout -text | grep -A 1 "Subject Alternative Name"
    ```
    You should see output similar to:
    ```
    X509v3 Subject Alternative Name:
        DNS:localhost, DNS:keycloak
    ```

**Resulting Files:**
After these steps, you will have the following important files in your `ViolentUTF_nightly/certs/` directory:
* `key.pem`: Your private key for Keycloak.
* `cert.pem`: Your self-signed public certificate, valid for `localhost` and `keycloak`.
* `openssl.cnf`: The configuration file used to generate the certificate.
* `csr.pem`: The certificate signing request (can be kept or deleted).
