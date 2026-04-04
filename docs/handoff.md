# АППК — Handoff (актуально на 04.04.2026)

## Статус проекта
- **Дата:** 04.04.2026
- **Сервер:** http://91.243.71.139 (Ubuntu 22.04, /opt/KGD_APPK)
- **Репозиторий:** https://github.com/kuanqk/KGD_APPK.git
- **Стек:** Django 4.2, PostgreSQL 15, Celery+Redis, xhtml2pdf, Docker Compose

---

## Что реализовано

### Основные спринты (S0–S10)
- Инфраструктура Docker, роли пользователей, AuditLog
- Реестр дел + карточка, автономер АД-01-20260317-0000001
- Документы + шаблоны (xhtml2pdf + DejaVu шрифт)
- Вручение нарочно / заказным письмом
- Возврат письма → Акт + Запрос в ДЭР
- Заслушивание + Протокол + дедлайн 2 рабочих дня
- Итоговые решения (прекращение / налоговая проверка)
- Согласование + возврат на доработку (ApprovalFlow)
- Уведомления + Celery Beat (bell-иконка)
- Отчёты + экспорт PDF/XLSX
- Безопасность + rate limit + backup

### Доработки после S10
- **P1:** Backdating — контроль дат с разрешением admin/reviewer
- **P2:** Новый формат номеров `ПРТ-02-20260315-0000001`
- **SA:** Просрочки — красные/жёлтые метки, Celery в 9:00
- **SB:** Дашборд по ролям (admin/reviewer/operator/observer)
- **SC:** Фильтр по офису, for_user() fix, импорт НП из Excel
- Обратная связь: модальная форма feedback в footer
- ИИН/БИН валидатор: KZValidator с metadata (дата рождения, пол)
- Справочники: Region, CaseCategory, CaseBasis, Position, Department, TaxAuthorityDetails
- Реквизиты КГД: множественный справочник, FK из Department

### Доработки после пилота (март–апрель 2026)
- **Вручение:** поле sent_at в форме + инлайн чекбокс/дата/файл в таблице дела
- **Основание:** basis → ManyToMany, множественный выбор чекбоксами
- **Категория:** category → ManyToMany, множественный выбор чекбоксами
- **Наблюдатели:** case_observers M2M — видят дело/документы, не создают; модальное окно на карточке
- **Протокол:** загрузка 3 файлов (подписанный протокол, удостоверение, доверенность)
- **fix:** Валидатор БИН — нестандартные даты регистрации (день=40), 7-я цифра 0
- **fix:** Форма вручения — валидация выбора документа перед отправкой

---

## Документы — текущий статус

| # | Тип | Статус |
|---|-----|--------|
| 1 | Извещение о явке | ✅ Готово |
| 2 | Предварительное решение | ✅ Готово |
| 3 | Протокол заслушивания | ✅ Готово |
| 4 | Акт налогового обследования | ⏳ Ждём форму от КГД |
| 5 | Запрос в ДЭР | ⏳ Ждём форму от КГД |
| 6 | Решение о прекращении дела | ⏳ Ждём обратную связь |
| 7 | Инициирование внеплановой проверки | ⏳ Ждём форму от КГД |
| 8 | Приказ о назначении проверки | ⏳ Ждём форму от КГД |

---

## Задачи в очереди

### Приоритет 1 — Документы 4–8
Нужны Word-файлы с выделением жёлтым/зелёным для каждого документа.
После получения — реализация по образцу документов 1–3 (двухколоночная форма).

### Приоритет 2 — После пилота
- **Матрица прав доступа** — гранулярные разрешения по модулям (роль × функция с чекбоксами).
  Затронет все views. Минимум 1–2 спринта. Отложено до завершения пилота.
- **П7 (решение о прекращении)** — ждём уточнений от пользователей.

---

## Архитектура

```
apps/
├── accounts/      # User, роли, Department FK
├── cases/         # AdministrativeCase, Taxpayer, справочники
├── documents/     # CaseDocument, шаблоны, генерация PDF
├── delivery/      # DeliveryRecord
├── hearings/      # Hearing, HearingProtocol
├── decisions/     # FinalDecision
├── approvals/     # ApprovalFlow
├── notifications/ # Notification, Celery tasks
├── audit/         # AuditLog
├── reports/       # отчёты, экспорт
└── feedback/      # Feedback (пилот)

templates/         # все HTML шаблоны (не внутри apps)
docs/
├── architecture/  # overview, models, urls
├── apps/          # документация каждого приложения
├── dev/           # setup, workflow, conventions, claude_prompts
├── ops/           # deploy, backup
└── business/      # flow, roles
```

---

## Деплой

```bash
# Локально
git add .
git commit -m "feat(...): описание"
git push

# На сервере (без миграций)
cd /opt/KGD_APPK && git pull && docker compose restart web

# На сервере (с миграциями)
cd /opt/KGD_APPK && git pull && \
docker compose run --rm web python manage.py migrate && \
docker compose restart web

# Конфликт миграций
docker compose run --rm web python manage.py makemigrations --merge --no-input && \
docker compose run --rm web python manage.py migrate
```

---

## Шорткоды для Claude Code

| Код | Значение |
|-----|---------|
| [S0]-[S10] | Спринты 0-10 |
| [P1] | Backdating |
| [P2] | Формат номеров |
| [SA] | Просрочки |
| [SB] | Дашборд |
| [SC] | Фильтр офисов |
| [BUG] | Баг-репорт |
| [DB] | Миграция |
| [DOC4]-[DOC8] | Документы 4-8 |

---

## Важные файлы для нового разработчика

```
docs/handoff.md              ← начни отсюда (этот файл)
docs/architecture/overview.md ← стек, сервисы, структура
docs/architecture/models.md   ← все модели данных
docs/architecture/urls.md     ← все URL-маршруты
docs/apps/<appname>.md        ← документация конкретного приложения
docs/dev/setup.md             ← как запустить локально
docs/dev/workflow.md          ← как деплоить
docs/dev/conventions.md       ← соглашения по коду
docs/dev/claude_prompts.md    ← как писать промпты для Claude Code
docs/business/flow.md         ← бизнес-процесс
docs/business/roles.md        ← роли и матрица доступа
docs/pilot_guide.md           ← инструкция для пользователей
```
