# Онбординг разработчика (~15 минут)

Цель: поднять проект локально и знать, куда смотреть дальше без обхода всего репозитория.

## Шаг 1 — контекст (5 мин)

1. Прочитать [`docs/handoff.md`](../handoff.md) — статус, что сделано, деплой, шорткоды.
2. Просмотреть [`docs/architecture/overview.md`](../architecture/overview.md) — стек и сервисы Docker.

## Шаг 2 — запуск (10 мин)

Следовать [`docs/dev/setup.md`](setup.md): клонирование, `.env`, `docker compose up -d`, `migrate`, `createsuperuser`.

После старта приложение доступно по **`http://localhost:8000/`** (в `docker-compose.yml` порт **8000**).

Дальше — обязательные шаги из setup: офисы в Admin, подразделения пользователям, `StagnationSettings`.

## Шаг 3 — работа по задаче

- Общие правила: [`docs/dev/conventions.md`](conventions.md).
- Бизнес-процесс: [`docs/business/flow.md`](../business/flow.md).
- Конкретный Django-app: **`docs/apps/<имя>.md`** (например `cases`, `documents`) — минимальный контекст для изменений без чтения всего кода.

## Справочник путей

| Нужно | Файл |
|-------|------|
| Модели | [`docs/architecture/models.md`](../architecture/models.md) |
| URL | [`docs/architecture/urls.md`](../architecture/urls.md) |
| Деплой / бэкап | [`docs/ops/deploy.md`](../ops/deploy.md), [`docs/ops/backup.md`](../ops/backup.md) |
| Полный обзор продукта | [`docs/README.md`](../README.md) |

Исторические материалы: [`docs/archive/`](../archive/).
