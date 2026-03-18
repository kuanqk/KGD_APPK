#!/usr/bin/env bash
set -e

NGINX_CONF="/etc/nginx/sites-enabled/myapp"

# Если есть бэкап — восстанавливаем напрямую
if [ -f "${NGINX_CONF}.bak" ]; then
    cp "${NGINX_CONF}.bak" "$NGINX_CONF"
    rm -f "${NGINX_CONF}.bak"
    echo "nginx config restored from backup"
else
    # Бэкапа нет — правим конфиг скриптом
    python3 - "$NGINX_CONF" <<'PYEOF'
import sys, re

path = sys.argv[1]
text = open(path).read()

# Удалить строки error_page и location = /maintenance.html
text = re.sub(r'\s*error_page 503 /maintenance\.html;\n', '\n', text)
text = re.sub(r'\s*location = /maintenance\.html \{ root /var/www/html; internal; \}\n', '', text)

# Восстановить location / с proxy_pass
text = re.sub(
    r'(location\s+/\s*\{)\s*return 503;\s*(\})',
    (
        r'\1\n'
        r'        proxy_pass http://127.0.0.1:8000;\n'
        r'        proxy_set_header Host $host;\n'
        r'        proxy_set_header X-Real-IP $remote_addr;\n'
        r'        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n'
        r'    \2'
    ),
    text,
    count=1,
    flags=re.DOTALL,
)

open(path, 'w').write(text)
print("nginx config updated: maintenance OFF")
PYEOF
fi

# Перезагружаем nginx
nginx -t && nginx -s reload
echo "Maintenance mode: OFF"
