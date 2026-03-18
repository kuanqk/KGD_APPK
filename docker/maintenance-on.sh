#!/usr/bin/env bash
set -e

NGINX_CONF="/etc/nginx/sites-enabled/myapp"
MAINTENANCE_HTML="/var/www/html/maintenance.html"

# 1. Создаём страницу техобслуживания
mkdir -p /var/www/html
cat > "$MAINTENANCE_HTML" <<'EOF'
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Система временно недоступна — АППК</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f4f8;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            color: #2d3748;
        }
        .card {
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.10);
            padding: 56px 48px;
            max-width: 520px;
            width: 90%;
            text-align: center;
        }
        .icon { font-size: 56px; margin-bottom: 20px; }
        .brand {
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #718096;
            margin-bottom: 12px;
        }
        h1 {
            font-size: 22px;
            font-weight: 700;
            color: #1a202c;
            margin-bottom: 16px;
        }
        p {
            font-size: 15px;
            line-height: 1.7;
            color: #4a5568;
            margin-bottom: 12px;
        }
        .divider {
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 28px 0;
        }
        .support {
            font-size: 13px;
            color: #718096;
        }
        .support a {
            color: #3182ce;
            text-decoration: none;
        }
        .status-badge {
            display: inline-block;
            background: #fff8e1;
            color: #b7791f;
            border: 1px solid #f6d860;
            border-radius: 20px;
            padding: 4px 16px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 24px;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🔧</div>
        <div class="brand">АППК — КГД МФ РК</div>
        <span class="status-badge">Технические работы</span>
        <h1>Система временно недоступна</h1>
        <p>Проводятся плановые технические работы по обновлению системы.<br>
           Пожалуйста, повторите попытку через несколько минут.</p>
        <p>Приносим извинения за временные неудобства.</p>
        <hr class="divider">
        <div class="support">
            По вопросам обращайтесь в техническую поддержку:<br>
            <a href="mailto:support@kgd.gov.kz">support@kgd.gov.kz</a>
        </div>
    </div>
</body>
</html>
EOF

# 2. Бэкап текущего конфига
cp "$NGINX_CONF" "${NGINX_CONF}.bak"

# 3. Вставляем error_page и location /maintenance.html перед "location /"
#    и заменяем тело location / на return 503
python3 - "$NGINX_CONF" <<'PYEOF'
import sys, re

path = sys.argv[1]
text = open(path).read()

# Вставить error_page + maintenance location перед "location /"
maintenance_block = (
    "    error_page 503 /maintenance.html;\n"
    "    location = /maintenance.html { root /var/www/html; internal; }\n"
    "    "
)
text = re.sub(r'(\s*location\s+/\s*\{)', maintenance_block + r'\1', text, count=1)

# Заменить содержимое location / на return 503
text = re.sub(
    r'(location\s+/\s*\{)[^}]*(})',
    r'\1\n        return 503;\n    \2',
    text,
    count=1,
    flags=re.DOTALL,
)

open(path, 'w').write(text)
print("nginx config updated: maintenance ON")
PYEOF

# 4. Перезагружаем nginx
nginx -t && nginx -s reload
echo "Maintenance mode: ON"
