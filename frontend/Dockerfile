FROM nginx:alpine

RUN apk add --no-cache gettext

COPY index.html /usr/share/nginx/html/index.html.template
COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template

# Cloud Run injects PORT; BACKEND_URL is set per-service at deploy time.
ENV PORT=8080
ENV BACKEND_URL=http://localhost:8080

RUN printf '#!/bin/sh\nset -e\nenvsubst "\\$BACKEND_URL" < /usr/share/nginx/html/index.html.template > /usr/share/nginx/html/index.html\nenvsubst "\\$PORT" < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf\nexec nginx -g "daemon off;"\n' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
