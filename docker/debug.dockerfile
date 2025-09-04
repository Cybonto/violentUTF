# Minimal secure debug container with essential network tools
FROM alpine:3.19

# Install only essential debugging tools
RUN apk add --no-cache \
    curl \
    bind-tools \
    iputils \
    busybox-extras

# Run as non-root user for security
RUN adduser -D -u 1001 debugger
USER debugger

# Keep container running
CMD ["sh", "-c", "echo 'Debug container ready. Use docker exec -it <container> sh to enter.' && tail -f /dev/null"]
