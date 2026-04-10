# Пилот с КГД: обратная связь, выкаты и доработки

Документ фиксирует **что сделано** в рамках обработки обращений пилота (примерно **pk 37–71**), **где лежит код**, **как выкатывать** и **что настроить в админке**. Обновляйте при появлении новых волн отзывов.

---

## 1. Краткое содержание

| Тема | Суть |
|------|------|
| Бэклог | Структурированный список тем обращений по категориям — `apps/feedback/backlog.py` |
| Массовые ответы в БД | Команды `apply_feedback_responses_37_63`, `apply_feedback_responses_64_71` |
| Выгрузка текстов с сервера | `dump_feedback_range --min N --max M` |
| Реквизиты КГД и регион | Поле **регион** у `TaxAuthorityDetails`, логика подбора в `_get_authority_details` |
| Протокол из заслушивания | PDF через `generate_hearing_protocol` с данными из `Hearing` (место, дата, время, итог) |
| Срок после протокола | **3 рабочих дня** на замечания к протоколу (ориентир п. 6 ст. 74 АППК) |
| PDF инициирования проверки | Миграция дополняет шаблон блоком подписи/даты |
| Большие формы (413) | Лимиты в `config/settings/base.py`; при 413 за **nginx** — поднять `client_max_body_size` |
| Celery Beat | Файл `celerybeat-schedule` в `.gitignore`, не хранить в git |

---

## 2. Файлы и модули

### Обратная связь и бэклог

| Путь | Назначение |
|------|------------|
| `apps/feedback/models.py` | Модель `Feedback`, статусы |
| `apps/feedback/backlog.py` | `FEEDBACK_BACKLOG`, `RESOLVED_FEEDBACK_IDS`, `items_by_category()` |
| `apps/feedback/management/commands/apply_feedback_responses_37_63.py` | Проставление ответов **37–63** |
| `apps/feedback/management/commands/apply_feedback_responses_64_71.py` | Проставление ответов **64–71** |
| `apps/feedback/management/commands/dump_feedback_range.py` | Выгрузка pk-диапазона (plain / `--markdown`) |

### Дела и реквизиты

| Путь | Назначение |
|------|------------|
| `apps/cases/models.py` | `TaxAuthorityDetails`: поле **`region`** (FK на `Region`, опционально) |
| `apps/cases/migrations/0017_taxauthoritydetails_region.py` | Миграция поля региона |
| `apps/cases/admin.py` | Админка: `region` в списке и `raw_id_fields` |

### Документы и PDF

| Путь | Назначение |
|------|------------|
| `apps/documents/services.py` | `_get_authority_details`, `get_document_context` (в т.ч. `deputy_position`), `generate_hearing_protocol` (поле **`venue`** подменяет адрес в шапке протокола) |
| `apps/documents/forms.py` | `HearingProtocolForm`: поле **`venue`** |
| `apps/documents/views.py` | `HearingProtocolFormView`: подсказки в `auto_fields` |
| `apps/documents/migrations/0022_audit_initiation_signatures.py` | Шаблон `audit_initiation`: блок подписи |
| `templates/documents/hearing_protocol_form.html` | Поле «Место проведения» |

### Заслушивания

| Путь | Назначение |
|------|------------|
| `apps/hearings/services.py` | `create_protocol`: вызывает **`generate_hearing_protocol`**, `_hearing_protocol_form_data_from_hearing`, дедлайн **3** р.д. |
| `apps/hearings/models.py` | `HearingProtocol.deadline_2days` — обновлённый `verbose_name` |
| `apps/hearings/migrations/0003_alter_hearingprotocol_deadline_2days.py` | Миграция подписи поля |
| `apps/hearings/views.py` | Сообщение после оформления протокола |
| `templates/hearings/protocol_create.html` | Текст про **3 рабочих дня** и п. 6 ст. 74 АППК |

### Настройки

| Путь | Назначение |
|------|------------|
| `config/settings/base.py` | `DATA_UPLOAD_MAX_MEMORY_SIZE`, `FILE_UPLOAD_MAX_MEMORY_SIZE` (32 МБ) |
| `.gitignore` | `celerybeat-schedule`, `celerybeat-schedule.*` |

### Прочее (ранее по пилоту)

| Путь | Назначение |
|------|------------|
| `apps/cases/views.py` | `CaseListView`: фильтр по региону (`region__name__icontains` / `region__code__icontains`) |

---

## 3. Команды на сервере

Выполнять **из каталога проекта**, не внутри `manage.py shell`:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py apply_feedback_responses_64_71 --dry-run
docker compose exec web python manage.py apply_feedback_responses_64_71
docker compose exec web python manage.py dump_feedback_range --min 64 --max 71
docker compose restart web
```

После изменений кода: `git pull` → `migrate` → при необходимости команды ответов → `restart web`. Worker/beat перезапускать при изменениях в задачах Celery или расписании.

---

## 4. Настройка реквизитов КГД под регион

1. Админка: **Реквизиты КГД** (`TaxAuthorityDetails`).
2. Логика подбора для PDF: сначала запись с тем же **подразделением**, что у дела; если нет — запись с **регионом**, совпадающим с `AdministrativeCase.region`; иначе первая активная запись.
3. Для регионов вроде **СКО** при расхождении офиса и региона заведите отдельную строку реквизитов с заполненным **регионом**.

---

## 5. Интеграция с КНП (личный кабинет НП)

В **пилоте** интеграции с внешними ИС (в т.ч. КНП) **не реализуются**; в текстах ответов это зафиксировано для обращений **39, 40, 56, 64 (п. 1)**. После пилота — отдельное ТЗ с КГД.

---

## 6. Git и `celerybeat-schedule`

Файл создаётся Celery Beat локально/на сервере. Если он уже был в репозитории, выполнить **один раз**:

```bash
git rm --cached celerybeat-schedule
git commit -m "chore: stop tracking celerybeat-schedule"
```

Файл на диске может остаться; в git попадать не должен.

---

## 7. Nginx и ошибка 413

Лимиты в Django см. раздел «Настройки». Если 413 приходит **до** приложения, на прокси нужно увеличить **`client_max_body_size`** (не входит в этот репозиторий — настраивается на стороне инфраструктуры).

---

## 8. Связанные документы

- Общий обзор: [`docs/README.md`](README.md)
- Заслушивания: [`docs/apps/hearings.md`](apps/hearings.md) (при расхождении с этим файлом **приоритет у `pilot_feedback_rollout.md`** по срокам и протоколу)
- Деплой: [`docs/ops/deploy.md`](ops/deploy.md)

---

*Документ отражает состояние репозитория на момент ввода доработок по пилотной обратной связи (апрель 2026).*
