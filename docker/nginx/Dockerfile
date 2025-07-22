# =============================================================================
# Nginx Reverse Proxy and Load Balancer
# =============================================================================
# Custom Nginx configuration with SSL support, load balancing,
# static file serving, and security enhancements
# =============================================================================

FROM nginx:1.25-alpine

# Install additional packages
RUN apk add --no-cache \
    curl \
    certbot \
    certbot-nginx \
    logrotate \
    openssl \
    netcat-openbsd \
    bash \
    && rm -rf /var/cache/apk/*

# Create nginx user directories
RUN mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp \
             /var/log/nginx \
             /etc/nginx/ssl \
             /var/www/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/
COPY ssl/ /etc/nginx/ssl/

# Copy static files and error pages
COPY html/ /var/www/html/

# Copy scripts
COPY scripts/ /usr/local/bin/
RUN chmod +x /usr/local/bin/*.sh

# Create log rotation configuration
COPY logrotate.conf /etc/logrotate.d/nginx

# Set proper permissions
RUN chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && chown -R nginx:nginx /var/www/html \
    && chmod 755 /var/cache/nginx \
    && chmod 755 /var/log/nginx

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Use custom entrypoint for SSL setup
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]

# Build metadata
LABEL description="Nginx reverse proxy with load balancing and SSL support"
LABEL version="1.0.0"