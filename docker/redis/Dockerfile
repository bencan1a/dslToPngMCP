# =============================================================================
# Redis Cache and Message Queue
# =============================================================================
# Custom Redis configuration with persistence, security,
# and performance optimizations for the DSL PNG service
# =============================================================================

FROM redis:7.2-alpine

# Install additional packages
RUN apk add --no-cache \
    curl \
    bash \
    && rm -rf /var/cache/apk/*

# Create redis directories
RUN mkdir -p /data/redis \
             /var/log/redis \
             /etc/redis/conf.d

# Copy custom redis configuration
COPY redis.conf /etc/redis/redis.conf
COPY conf.d/ /etc/redis/conf.d/

# Copy health check script
COPY scripts/health-check.sh /usr/local/bin/health-check.sh
RUN chmod +x /usr/local/bin/health-check.sh

# Set proper permissions
RUN chown -R redis:redis /data/redis \
    && chown -R redis:redis /var/log/redis \
    && chown -R redis:redis /etc/redis \
    && chmod 755 /data/redis \
    && chmod 755 /var/log/redis

# Switch to redis user
USER redis

# Expose Redis port
EXPOSE 6379

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD /usr/local/bin/health-check.sh

# Set working directory
WORKDIR /data

# Start Redis with custom configuration
CMD ["redis-server", "/etc/redis/redis.conf"]

# Build metadata
LABEL description="Redis cache and message queue with persistence"
LABEL version="1.0.0"