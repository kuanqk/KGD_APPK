# Резервное копирование

## Автоматически
Сервис `backup` в docker-compose.yml.
- Расписание: 02:00 ежедневно
- Хранение: последние 7 дней в томе `backup_data`
- Скрипт: `docker/backup/backup.sh`
- Файлы: **`/backups/appk_YYYYMMDD_HHMMSS.sql.gz`** (сжатый plain SQL)

## Вручную
```bash
# Запустить резервное копирование
docker compose exec backup /bin/sh /backup.sh

# Просмотр существующих резервных копий
docker compose exec backup ls -lh /backups/
```

## Восстановление из бэкапа

Дампы лежат в контейнере **`backup`**, том **`backup_data`**. В контейнере **`db`** пути к этим файлам нет — восстанавливайте потоком **из backup в psql**.

### 1. Остановить запись в БД
```bash
docker compose stop web worker beat
```

### 2. Восстановить из выбранного `.sql.gz`
Подставьте имя файла из `ls -lh /backups/` (пример ниже — шаблон).

```bash
docker compose exec -T backup gunzip -c /backups/appk_20260404_020015.sql.gz \
  | docker compose exec -T db psql -U "${POSTGRES_USER:-appk}" -d "${POSTGRES_DB:-appk}"
```

При необходимости задайте пользователя и имя БД явно, как в вашем `.env` (`POSTGRES_USER`, `POSTGRES_DB`).

### 3. Запустить приложение
```bash
docker compose start web worker beat
```

> **Важно:** восстановление перезаписывает данные в БД. Делайте на копии окружения или после свежего бэкапа текущего состояния.

## Тома Docker
| Том | Содержимое |
|-----|------------|
| postgres_data | Данные PostgreSQL |
| redis_data | Данные Redis |
| backup_data | Резервные копии БД |
