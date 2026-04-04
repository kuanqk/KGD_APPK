# App: documents

## Назначение
Генерация, хранение и предпросмотр процессуальных документов (PDF).

## Ключевые файлы
- `models.py` — CaseDocument, DocumentTemplate, DocumentType, DocumentStatus
- `views.py` — DocumentCreateView, NoticeFormView, PreliminaryDecisionFormView, PrintPreviewView
- `templates/documents/` — формы документов

## Минимальный контекст для задач
```
Передавай в Claude Code:
- docs/apps/documents.md (этот файл)
- apps/documents/models.py
- apps/documents/views.py
- templates/documents/<нужный шаблон>.html
```

## 8 типов документов
| # | Тип (doc_type) | Отображение | Префикс | Статус формы |
|---|----------------|------------|---------|-------------|
| 1 | notice | Извещение о явке | ИЗВ | ✅ Готово |
| 2 | preliminary_decision | Предварительное решение | ПРД | ✅ Готово |
| 3 | hearing_protocol | Протокол заслушивания | ПРТ | ✅ Готово |
| 4 | inspection_act | Акт налогового обследования | АКТ | ⏳ Нужна форма |
| 5 | der_request | Запрос в ДЭР | ДЭР | ⏳ Нужна форма |
| 6 | termination_decision | Решение о прекращении | ПРК | ⏳ Нужна форма |
| 7 | audit_initiation | Инициирование внеплановой проверки | ВНП | ⏳ Нужна форма |
| 8 | audit_order | Приказ о назначении проверки | — | ⏳ Нужна форма |

## Логика форм (1-3)
- Две колонки: форма слева, предпросмотр справа
- Жёлтые поля = авто из БД (readonly), зелёные = ручной ввод
- Валидация дат: не раньше даты дела (кроме allow_backdating)
- PDF сохраняется в системе + кнопка "Предпросмотр для печати"
- `context_snapshot` сохраняется в `metadata` JSONField для корректного предпросмотра

## Правила
- `signed` документы нельзя удалять → только новая версия (version++)
- `is_deletable` property → False если status == signed
- Нумерация: `PREFIX-КОД-YYYYMMDD-NNNNNNN` через `Department.doc_sequence`

## DocumentTemplate
Хранит Django template syntax в поле `body_template`.
При сохранении нового активного шаблона — деактивирует предыдущие того же типа.

## Предпросмотр для печати
URL: `/documents/<pk>/print/` → `PrintPreviewView`
Рендерит HTML из `metadata["context_snapshot"]` без генерации нового PDF.

## Наблюдатели и документы
`DocumentCreateView.dispatch()` проверяет `case.case_observers.filter(pk=user.pk).exists()`.
Если пользователь — только наблюдатель → redirect с сообщением об ошибке.
