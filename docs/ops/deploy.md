# Деплой и эксплуатация

## Сервер
- IP: 91.243.71.139
- Путь: /opt/KGD_APPK
- ОС: Ubuntu 22.04 LTS
- Управление: Docker Compose

## Стандартный деплой (без миграций)
```bash
cd /opt/KGD_APPK
git pull
docker compose restart web worker beat
```

После изменений в **коде Celery-задач** (`apps/*/tasks.py`, `services.py`, вызываемых из worker) без перезапуска **`worker`** воркер продолжит старую логику. Для правок в **расписании** Beat — перезапуск **`beat`**.

## Деплой с миграциями
```bash
cd /opt/KGD_APPK
git pull
docker compose run --rm web python manage.py migrate
docker compose restart web worker beat
```

## Makefile команды
```bash
make up              # поднять все сервисы
make down            # остановить
make deploy          # git pull + restart web worker beat
make migrate         # применить миграции
make maintenance-on  # включить режим обслуживания
make maintenance-off # выключить режим обслуживания
make logs            # просмотр логов
make test            # запустить тесты
make shell           # django shell_plus
```

## Полный цикл деплоя с maintenance
```bash
# Локально
make maintenance-on
git add .
git commit -m "feat(...): описание"
git push

# На сервере
cd /opt/KGD_APPK
git pull
docker compose run --rm web python manage.py migrate  # если есть миграции
docker compose restart web worker beat

# Локально
make maintenance-off
```

## Конфликты миграций
```bash
ssh root@91.243.71.139 'cd /opt/KGD_APPK && \
  chmod -R 777 apps/*/migrations && \
  docker compose run --rm web python manage.py makemigrations --merge --no-input && \
  docker compose run --rm web python manage.py migrate'
docker compose restart web worker beat
```

## Просмотр логов
```bash
docker compose logs -f web     # логи приложения
docker compose logs -f worker  # логи Celery worker
docker compose logs -f beat    # логи Celery Beat (расписание)
docker compose logs -f db      # логи PostgreSQL
```

## Продакшн настройки (config/settings/prod.py)
- SECURE_HSTS_SECONDS = 31536000
- SECURE_SSL_REDIRECT = True
- SESSION_COOKIE_SECURE = True
- CSRF_COOKIE_SECURE = True
- X_FRAME_OPTIONS = "DENY"

## Celery — проверка задач вручную
```bash
docker compose exec web celery -A config call notifications.tasks.check_deadlines
docker compose exec web celery -A config call notifications.tasks.check_stagnant_cases
```
