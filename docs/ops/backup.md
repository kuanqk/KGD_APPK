# Резервное копирование

## Автоматически
Сервис `backup` в docker-compose.yml.
- Расписание: 02:00 ежедневно
- Хранение: последние 7 дней в томе `backup_data`
- Скрипт: `docker/backup/backup.sh`

## Вручную
```bash
# Запустить резервное копирование
docker compose exec backup /bin/sh /backup.sh

# Просмотр существующих резервных копий
docker compose exec backup ls -lh /backups/
```

## Восстановление из бэкапа
```bash
# Остановить приложение
docker compose stop web worker

# Восстановить БД
docker compose exec db psql -U appk appk < /backups/backup_YYYYMMDD.sql

# Запустить приложение
docker compose start web worker
```

## Тома Docker
| Том | Содержимое |
|-----|-----------|
| postgres_data | Данные PostgreSQL |
| redis_data | Данные Redis |
| backup_data | Резервные копии БД |
