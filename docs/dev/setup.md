# Настройка среды разработки

## Требования
- Docker и Docker Compose
- Git

## Быстрый старт
```bash
git clone https://github.com/kuanqk/KGD_APPK.git
cd KGD_APPK
cp .env.example .env
# Отредактировать .env

docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

## Первый запуск после migrate
```bash
# 1. Создать офисы в Django Admin
# http://localhost:8000/admin/cases/department/
# Коды 01-20, наименования подразделений

# 2. Назначить офисы пользователям
# http://localhost:8000/users/ → Редактировать → поле Подразделение

# 3. Настроить порог застывших дел
# http://localhost:8000/admin/cases/stagnationsettings/
# stagnation_days (default 30), notify_reviewer
```

## Переменные окружения (.env)
```env
SECRET_KEY=your-secret-key
DJANGO_SETTINGS_MODULE=config.settings.dev
ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=appk
POSTGRES_USER=appk
POSTGRES_PASSWORD=appk
POSTGRES_HOST=db
REDIS_URL=redis://redis:6379/0
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@appk.kz
EMAIL_HOST_PASSWORD=your-email-password
SITE_URL=http://localhost:8000
```

## Полезные команды
```bash
make up                    # поднять все сервисы
make down                  # остановить
make migrate               # применить миграции
make test                  # тесты
docker compose logs -f web # логи приложения
docker compose exec web python manage.py shell_plus
docker compose exec web python manage.py makemigrations --check
```

## Зависимости (requirements/)
- `base.txt` — Django, psycopg2, celery, redis, xhtml2pdf, openpyxl
- `dev.txt` — debug-toolbar, factory-boy, coverage
- `prod.txt` — sentry-sdk
