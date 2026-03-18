.PHONY: up down build migrate makemigrations test shell createsuperuser logs collectstatic deploy maintenance-on maintenance-off

# Запуск всех сервисов
up:
	docker compose up -d

# Запуск с выводом логов
up-logs:
	docker compose up

# Остановка всех сервисов
down:
	docker compose down

# Пересборка образов
build:
	docker compose build

# Применить миграции
migrate:
	docker compose exec web python manage.py migrate

# Создать миграции
makemigrations:
	docker compose exec web python manage.py makemigrations

# Проверить что миграции актуальны (для pre-commit)
check-migrations:
	docker compose exec web python manage.py makemigrations --check

# Запустить тесты
test:
	docker compose exec web python manage.py test apps --verbosity=2

# Открыть Django shell
shell:
	docker compose exec web python manage.py shell_plus

# Создать суперпользователя
createsuperuser:
	docker compose exec web python manage.py createsuperuser

# Логи web-сервиса
logs:
	docker compose logs -f web

# Логи worker-сервиса
logs-worker:
	docker compose logs -f worker

# Собрать статику
collectstatic:
	docker compose exec web python manage.py collectstatic --noinput

# Деплой на сервер
deploy:
	@ssh root@91.243.71.139 'cd /opt/KGD_APPK && git pull && docker compose restart web'

# Режим обслуживания
maintenance-on:
	@ssh root@91.243.71.139 'bash /opt/KGD_APPK/docker/maintenance-on.sh'

maintenance-off:
	@ssh root@91.243.71.139 'bash /opt/KGD_APPK/docker/maintenance-off.sh'
