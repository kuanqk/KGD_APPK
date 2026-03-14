# АППК — Автоматизированная Платформа Производства по делам об Административных Правонарушениях

Веб-система для управления административными делами в органах КГД РК. Автоматизирует полный цикл: создание уведомлений → вручение документов → возврат по почте → заслушивание → вынесение решения (прекращение или назначение налоговой проверки).

## Технологии

- **Backend**: Python 3.11, Django 4.2
- **База данных**: PostgreSQL 15
- **Очереди задач**: Celery + Redis
- **Веб-сервер**: Gunicorn + Nginx
- **Экспорт**: WeasyPrint (PDF), openpyxl (XLSX)
- **Контейнеризация**: Docker Compose

## Роли пользователей

| Роль | Доступ |
|------|--------|
| `admin` | Полный доступ: дела, документы, пользователи, лог системы, согласование |
| `operator` | Дела, документы, вручение, заслушивания |
| `reviewer` | Согласование решений, заслушивания, отчёты |
| `observer` | Только заслушивания и отчёты (без доступа к делам) |

## Быстрый старт

### Требования

- Docker и Docker Compose
- Git

### Запуск (разработка)

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd KGD_APPK

# 2. Создать файл окружения
cp .env.example .env
# Отредактировать .env (SECRET_KEY, пароли и т.д.)

# 3. Запустить все сервисы
docker compose up -d

# 4. Применить миграции и создать суперпользователя
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

# 5. Открыть браузер
# http://localhost/         — основное приложение
# http://localhost/admin/   — Django Admin
```

### Переменные окружения (`.env`)

```env
SECRET_KEY=your-secret-key-here-change-in-production
DJANGO_SETTINGS_MODULE=config.settings.dev
ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=appk
POSTGRES_USER=appk
POSTGRES_PASSWORD=appk_secure_password
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0

# Email (для уведомлений)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@appk.kz
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@appk.kz
```

## Структура проекта

```
KGD_APPK/
├── apps/
│   ├── accounts/       # Пользователи, аутентификация, управление
│   ├── cases/          # Административные дела
│   ├── documents/      # Документы по делам
│   ├── delivery/       # Вручение уведомлений
│   ├── hearings/       # Заслушивания
│   ├── decisions/      # Итоговые решения
│   ├── approvals/      # Механизм согласования (ApprovalFlow)
│   ├── notifications/  # Уведомления и Celery-задачи
│   ├── reports/        # Отчёты и экспорт PDF/XLSX
│   └── audit/          # Лог системных действий
├── config/
│   ├── settings/
│   │   ├── base.py     # Общие настройки
│   │   ├── dev.py      # Разработка (DEBUG=True, debug_toolbar)
│   │   └── prod.py     # Продакшн (HTTPS, HSTS, безопасные куки)
│   ├── urls.py
│   └── celery.py
├── templates/          # HTML-шаблоны (Django template language)
├── docker/
│   ├── web/Dockerfile
│   ├── nginx/default.conf
│   └── backup/backup.sh
├── docker-compose.yml
└── .env.example
```

## Разработка

### Полезные команды

```bash
# Запустить только БД и Redis (для локальной разработки без Docker)
docker compose up db redis -d

# Просмотр логов
docker compose logs -f web
docker compose logs -f worker

# Открыть shell Django
docker compose exec web python manage.py shell_plus

# Создать миграции
docker compose exec web python manage.py makemigrations

# Запустить тесты
docker compose exec web python manage.py test

# Проверить Celery задачи вручную
docker compose exec web celery -A config call notifications.tasks.check_deadlines
```

### Настройки модулей

| Приложение | Назначение | Ключевые файлы |
|------------|-----------|----------------|
| `accounts` | Кастомный User с ролями | `models.py`, `services.py` |
| `cases` | Жизненный цикл дела (статусы) | `models.py`, `services.py` |
| `delivery` | Вручение и возврат документов | `models.py`, `services.py` |
| `hearings` | Заслушивания, календарь | `models.py`, `services.py` |
| `decisions` | Прекращение / налоговая проверка | `models.py`, `services.py` |
| `approvals` | Workflow согласования | `models.py`, `services.py` |
| `notifications` | Уведомления + email + Celery Beat | `services.py`, `tasks.py` |
| `reports` | 9 типов отчётов, PDF/XLSX | `services.py`, `exporters.py` |
| `audit` | Иммутабельный лог действий | `models.py`, `middleware.py` |

## Резервное копирование

Сервис `backup` в `docker-compose.yml` автоматически делает резервную копию PostgreSQL каждый день в 02:00 (по времени контейнера) и хранит последние 7 дней в томе `backup_data`.

```bash
# Ручной запуск резервного копирования
docker compose exec backup /backup.sh

# Просмотр существующих резервных копий
docker compose exec backup ls -lh /backups/
```

## Продакшн-деплой

```bash
# 1. Скопировать .env и настроить продакшн-значения
cp .env.example .env
# SECRET_KEY — уникальный случайный ключ
# ALLOWED_HOSTS — реальное доменное имя
# POSTGRES_PASSWORD — надёжный пароль
# EMAIL_* — SMTP настройки

# 2. Изменить DJANGO_SETTINGS_MODULE
# В .env: DJANGO_SETTINGS_MODULE=config.settings.prod

# 3. Запустить
docker compose up -d

# 4. Применить миграции
docker compose exec web python manage.py migrate

# 5. Создать суперпользователя
docker compose exec web python manage.py createsuperuser
```

Продакшн-настройки (`config/settings/prod.py`) включают:
- `SECURE_HSTS_SECONDS = 31536000`
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `X_FRAME_OPTIONS = "DENY"`

## Celery Beat расписание

| Задача | Расписание | Описание |
|--------|-----------|----------|
| `check_deadlines` | Каждый час | Уведомления об истекающих и просроченных делах |
| `send_pending_emails` | Каждые 30 минут | Email-рассылка непрочитанных уведомлений |

## Лицензия

Проект разработан для внутреннего использования КГД РК.
