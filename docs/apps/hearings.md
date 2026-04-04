# App: hearings

## Назначение
Управляет заслушиваниями и протоколами. После протокола — отсчёт 2 рабочих дней.

## Ключевые файлы
- `models.py` — Hearing, HearingProtocol
- `services.py` — schedule_hearing, complete_hearing, create_protocol
- `views.py` — HearingScheduleView, HearingDetailView, HearingCompleteView, ProtocolCreateView
- `forms.py` — HearingScheduleForm, ProtocolCreateForm

## Минимальный контекст для задач
```
Передавай в Claude Code:
- docs/apps/hearings.md (этот файл)
- apps/hearings/models.py
- apps/hearings/views.py
- templates/hearings/<нужный шаблон>.html
```

## Шаблоны
```
templates/hearings/
├── calendar.html        — календарь заслушиваний
├── schedule.html        — форма назначения
├── detail.html          — карточка заслушивания
├── complete.html        — завершить заслушивание
└── protocol_create.html — оформить протокол
```

## Протокол (HearingProtocol)
OneToOne → Hearing. После сохранения:
- Вычисляется `deadline_2days` (2 рабочих дня от даты протокола)
- Дело переходит в статус `protocol_created`
- Celery-задача `check_deadlines` отслеживает дедлайн ежечасно

## Файлы протокола (≤5MB, PDF/JPG/PNG)
Загружаются в `media/hearings/protocols/YYYY/MM/`:
- `signed_protocol_file` — подписанный протокол НП
- `identity_doc_file` — удостоверение личности
- `power_of_attorney_file` — доверенность (если представитель)

Форма использует `enctype="multipart/form-data"`.
Валидация в `ProtocolCreateForm._validate_file()`.

## Форматы заслушивания
in_person / remote / mixed

## Участники
JSONField: список строк `["ФИО, должность", ...]`
