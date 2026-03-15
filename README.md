# АППК — Автоматизированная Платформа Производства по делам об Административных Правонарушениях

Веб-система для управления административными делами в органах КГД РК. Автоматизирует полный цикл: создание уведомлений → вручение документов → возврат по почте → заслушивание → вынесение решения (прекращение или назначение налоговой проверки).

## Функционал

- **Реестр дел** — создание, поиск, фильтрация по статусу / офису / ответственному / периоду
- **Документооборот** — генерация 8 типов процессуальных документов из шаблонов (PDF)
- **Вручение** — нарочно и заказным письмом, трекинг, фиксация возврата
- **Заслушивание** — назначение, протокол, отсчёт 2 рабочих дней (Celery)
- **Итоговые решения** — прекращение дела или инициирование налоговой проверки
- **Согласование** — workflow утверждения / возврата на доработку (ApprovalFlow)
- **Контроль дат (backdating)** — ввод документов задним числом только с разрешения руководителя
- **Застывшие дела** — автоматический мониторинг дел без движения, ежедневные уведомления
- **Дашборд по ролям** — разный контент для admin/reviewer (сводка по офисам) и operator/executor (мои дела, дедлайны)
- **Импорт НП из Excel** — массовая загрузка налогоплательщиков из .xlsx
- **Уведомления** — внутренние (bell-иконка) и email (Celery Beat)
- **Отчёты** — 10 типов, экспорт PDF и XLSX
- **Аудит** — иммутабельный лог всех действий

## Технологии

- **Backend**: Python 3.11, Django 4.2
- **База данных**: PostgreSQL 15
- **Очереди задач**: Celery + Redis
- **Веб-сервер**: Gunicorn + Nginx
- **PDF**: xhtml2pdf (без системных зависимостей, поддержка кириллицы через DejaVu)
- **Excel**: openpyxl (экспорт отчётов + импорт НП)
- **Контейнеризация**: Docker Compose

## Роли пользователей

| Роль | Видит дела | Создаёт дела | Согласует | Импорт НП | Дашборд |
|------|-----------|--------------|-----------|-----------|---------|
| `admin` | Все офисы | Да | Да | Да | Сводка по офисам |
| `reviewer` | Все офисы | Нет | Да | Нет | Сводка по офисам |
| `operator` | Свой офис | Да | Нет | Да | Мои дела + дедлайны |
| `executor` | Свои дела | Нет | Нет | Нет | Мои дела + дедлайны |
| `observer` | Свой офис (просмотр) | Нет | Нет | Нет | Счётчики региона |

### Логика for_user() (изоляция данных)

```python
def for_user(self, user):
    if user.role in ("admin", "reviewer"):
        return self                          # всё
    if user.role == "executor":
        return self.filter(responsible_user=user)
    # operator, observer — по офису; fallback на регион
    if user.department_id:
        return self.filter(department=user.department)
    if user.region:
        return self.filter(region=user.region)
    return self.none()
```

## Формат номеров документов

Новый формат (для дел с заполненным офисом):
```
PREFIX-КОД-YYYYMMDD-NNNNNNN
Пример: ИЗВ-05-20260316-0000042
```

Префиксы: `ИЗВ` · `ПРД` · `АКТ` · `ДЭР` · `ПРТ` · `ПРК` · `ВНП`

Старый формат `PREFIX-ГГГГ-NNNNN` сохраняется для дел без офиса (обратная совместимость).

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
# http://localhost/         — основное приложение (дашборд)
# http://localhost/admin/   — Django Admin
```

### Первый запуск — обязательные шаги после migrate

```bash
# Шаг 1: Создать офисы (подразделения)
# Открыть: http://localhost/admin/cases/department/
# Добавить офисы с кодами 01–20 и наименованиями

# Шаг 2: Назначить офисы пользователям
# Открыть: http://localhost/users/ → Редактировать каждого пользователя
# Поле "Подразделение" — выбрать соответствующий офис

# Шаг 3: Настроить порог застывших дел
# Открыть: http://localhost/admin/cases/stagnationsettings/
# Установить stagnation_days (по умолчанию 30) и notify_reviewer
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

SITE_URL=http://localhost:8000
```

## Структура проекта

```
KGD_APPK/
├── apps/
│   ├── accounts/       # Пользователи, аутентификация, управление
│   ├── cases/          # Административные дела, Department, StagnationSettings
│   ├── documents/      # Документы по делам, генерация PDF
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
├── docs/               # Документация проекта
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

# Проверить миграции перед коммитом
docker compose exec web python manage.py makemigrations --check

# Запустить тесты
docker compose exec web python manage.py test

# Проверить Celery задачи вручную
docker compose exec web celery -A config call notifications.tasks.check_deadlines
docker compose exec web celery -A config call notifications.tasks.check_stagnant_cases
```

### Настройки модулей

| Приложение | Назначение | Ключевые файлы |
|------------|-----------|----------------|
| `accounts` | Кастомный User с ролями и офисом | `models.py`, `forms.py` |
| `cases` | Жизненный цикл дела, Department, StagnationSettings | `models.py`, `services.py` |
| `delivery` | Вручение и возврат документов | `models.py`, `services.py` |
| `hearings` | Заслушивания, календарь | `models.py`, `services.py` |
| `decisions` | Прекращение / налоговая проверка | `models.py`, `services.py` |
| `approvals` | Workflow согласования | `models.py`, `services.py` |
| `notifications` | Уведомления + email + Celery Beat | `services.py`, `tasks.py` |
| `reports` | 10 типов отчётов, PDF/XLSX | `services.py`, `exporters.py` |
| `audit` | Иммутабельный лог действий | `models.py`, `middleware.py` |

## Celery Beat расписание

| Задача | Расписание | Описание |
|--------|-----------|----------|
| `check_deadlines` | Каждый час | Уведомления об истекающих и просроченных протоколах |
| `send_pending_emails` | Каждые 30 минут | Email-рассылка непрочитанных уведомлений |
| `check_stagnant_cases` | Ежедневно в 09:00 | Уведомление reviewer-ов о делах без движения |

## Резервное копирование

Сервис `backup` в `docker-compose.yml` автоматически делает резервную копию PostgreSQL каждый день в 02:00 и хранит последние 7 дней в томе `backup_data`.

```bash
# Ручной запуск резервного копирования
docker compose exec backup /bin/sh /backup.sh

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
# DJANGO_SETTINGS_MODULE=config.settings.prod

# 2. Запустить
docker compose up -d

# 3. Применить миграции
docker compose exec web python manage.py migrate

# 4. Создать суперпользователя
docker compose exec web python manage.py createsuperuser

# 5. Создать офисы и настроить пользователей (см. "Первый запуск")
```

Продакшн-настройки (`config/settings/prod.py`) включают:
- `SECURE_HSTS_SECONDS = 31536000`
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `X_FRAME_OPTIONS = "DENY"`

## Лицензия

Проект разработан для внутреннего использования КГД РК.
