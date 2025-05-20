# Use Node.js LTS version with multi-platform support
FROM node:20-slim

# Set environment variables
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=1
ENV NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/zscaler.pem

# Install required packages including PostgreSQL client
RUN apt-get update && apt-get install -y \
    build-essential \
    python3 \
    curl \
    libvips \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# # Install the ca-certificate package
# RUN apt-get update && apt-get install -y ca-certificates
# # Copy the CA certificate from the context to the build container
# COPY zscaler.crt /usr/local/share/ca-certificates/
# COPY zscaler.pem /usr/local/share/ca-certificates/
# COPY zscaler.pem /etc/ssl/certs/
# COPY CA.crt /usr/local/share/ca-certificates/
# RUN npm config set cafile /usr/local/share/ca-certificates/CA.crt
# # Update the CA certificates in the container
# RUN update-ca-certificates


# Create app directory
WORKDIR /opt/app

# Create wait-for-db script
RUN echo '#!/bin/sh\n\
set -e\n\
\n\
host="$1"\n\
shift\n\
cmd="$@"\n\
\n\
until pg_isready -h "$host" -U ${DATABASE_USERNAME:-strapi}; do\n\
  >&2 echo "Postgres is unavailable - sleeping"\n\
  sleep 2\n\
done\n\
\n\
>&2 echo "Postgres is up - executing command"\n\
exec $cmd' > /usr/local/bin/wait-for-db.sh && chmod +x /usr/local/bin/wait-for-db.sh

# Copy package.json and package-lock.json
COPY package.json package-lock.json ./

# Install dependencies using npm
RUN npm install

# Copy the rest of the app source code
COPY . .

# Expose Strapi port
EXPOSE 1337

# Start Strapi after waiting for DB
# CMD ["sh", "-c", "/usr/local/bin/wait-for-db.sh postgres_strapi && npm run develop"]

# Start Strapi after waiting for DB with debug flag
CMD ["sh", "-c", "/usr/local/bin/wait-for-db.sh postgres_strapi && npm run develop -- --debug"]