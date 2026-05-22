FROM nginx:alpine

# Install envsubst (comes with gettext)
RUN apk add --no-cache gettext

# Copy frontend source
COPY index.html /usr/share/nginx/html/index.html.template

# Default backend URL (can be overridden by environment variable)
ENV BACKEND_URL=http://localhost:8080

# Create a custom entrypoint script to inject the environment variable
RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'envsubst "\$BACKEND_URL" < /usr/share/nginx/html/index.html.template > /usr/share/nginx/html/index.html' >> /entrypoint.sh && \
    echo 'exec nginx -g "daemon off;"' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Update index.html.template to use the variable
# This will be handled in the next 'replace' turn or I can just write it correctly now.
# For now, I'll ensure the entrypoint is ready.

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
