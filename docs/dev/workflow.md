# Рабочий процесс разработки

## Цикл задачи
1. Описать задачу → написать промпт для Claude Code
2. Claude Code применяет изменения локально
3. Проверить результат
4. git commit + push
5. На сервере: git pull → migrate → restart

## Стандартный деплой (без миграций)
```bash
# Локально
git add .
git commit -m "feat(app): описание на английском"
git push

# На сервере
cd /opt/KGD_APPK
git pull
docker compose restart web worker beat
```

## Деплой с миграциями
```bash
# Локально
git add .
git commit -m "feat(cases): add new field"
git push

# На сервере
cd /opt/KGD_APPK
git pull
docker compose run --rm web python manage.py migrate
docker compose restart web worker beat
```

## С maintenance mode
```bash
make maintenance-on
git add . && git commit -m "..." && git push
# на сервере: git pull + migrate + restart
make maintenance-off
```

## Конфликты миграций (возникают регулярно)
```bash
docker compose run --rm web python manage.py makemigrations --merge --no-input
docker compose run --rm web python manage.py migrate
docker compose restart web worker beat
```

## Git commit messages (English)
```
feat(cases): add case_observers M2M field
fix(delivery): show validation error when no document selected
fix(validators): accept BIN with non-standard registration date
feat(hearings): add file uploads to hearing protocol
docs: restructure documentation
```

## Права на миграции (если ошибка permissions)
```bash
ssh root@91.243.71.139 'cd /opt/KGD_APPK && \
  chmod -R 777 apps/*/migrations && \
  docker compose run --rm web python manage.py makemigrations --merge --no-input && \
  docker compose run --rm web python manage.py migrate'
```
