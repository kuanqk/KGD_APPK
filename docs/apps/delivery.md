# App: delivery

## Назначение
Управляет вручением процессуальных документов налогоплательщику.

## Ключевые файлы
- `models.py` — DeliveryRecord, DeliveryMethod, DeliveryStatus
- `services.py` — create_delivery, mark_delivered, mark_returned
- `views.py` — DeliveryCreateView, DeliveryUpdateView, DeliveryUpdateInlineView
- `forms.py` — DeliveryCreateForm (с sent_at), DeliveryResultForm

## Минимальный контекст для задач
```
Передавай в Claude Code:
- docs/apps/delivery.md (этот файл)
- apps/delivery/models.py
- apps/delivery/views.py (если задача про views или AJAX)
- templates/delivery/create.html (если задача про форму)
- templates/cases/detail.html (если задача про таблицу вручения)
```

## Методы вручения
- `in_person` — нарочно (лично)
- `registered_mail` — заказное письмо (требует трек-номер)

## Статусы
- `pending` — ожидается подтверждение
- `delivered` — вручено
- `returned` — возвращено (только для registered_mail)

## Форма создания вручения
Поле `sent_at` (datetime-local) — обязательное, по умолчанию = текущий момент.
Backdating-валидация: если case.allow_backdating=False и роль не admin/reviewer — дата не раньше создания дела.
Валидация JS: если не выбран документ — показывает alert, блокирует submit.

## AJAX endpoint (update_inline)
`POST /delivery/<pk>/update-inline/` — `DeliveryUpdateInlineView`

Принимает:
| Параметр | Тип | Описание |
|----------|-----|---------|
| result_status | string | delivered / returned |
| delivered_at | date (YYYY-MM-DD) | Дата вручения |
| sent_at | datetime-local | Дата отправки |
| proof_file | file | PDF/JPG/PNG ≤2MB |

Возвращает JSON: `{ok, status, is_delivered, delivered_at, sent_at, proof_url}`

## Таблица вручения на карточке дела
Колонки: Документ / Метод / Трек-номер / Статус / Дата отправки / Вручено / Дата вручения / Файл / (Возврат)

Инлайн-редактирование (только pending + admin/operator):
- Дата отправки → datetime-local input → AJAX при change
- Вручено → checkbox → AJAX при change → location.reload()
- Дата вручения → date input → AJAX при change
- Файл → file input (скрытый, в label) → AJAX при change → location.reload()
- Кнопка "Возврат" → только для registered_mail → ведёт на delivery:update

## Файлы загружаются в
`media/delivery/proofs/YYYY/MM/`
