# Промпты для Claude Code — оптимизация токенов

## Принцип минимального контекста
Для каждой задачи передавай ТОЛЬКО нужные файлы.
Не передавай весь проект — это тратит токены впустую.

## Что передавать для каждого app

### cases (дела, НП, справочники)
```
docs/apps/cases.md
apps/cases/models.py
apps/cases/services.py  ← только если бизнес-логика
apps/cases/views.py     ← только если views
apps/cases/forms.py     ← только если формы
templates/cases/<нужный>.html
```

### delivery (вручение)
```
docs/apps/delivery.md
apps/delivery/models.py
apps/delivery/views.py
templates/delivery/create.html  ← форма вручения
templates/cases/detail.html     ← таблица вручения
```

### hearings (заслушивания)
```
docs/apps/hearings.md
apps/hearings/models.py
apps/hearings/views.py
templates/hearings/<нужный>.html
```

### documents (документы, PDF)
```
docs/apps/documents.md
apps/documents/models.py
apps/documents/views.py
templates/documents/<нужный>.html
```

### decisions (решения)
```
docs/apps/decisions.md
apps/decisions/models.py
apps/decisions/views.py
```

## Шорткоды (начало промпта)
| Код | Значение |
|-----|---------|
| [S0]-[S10] | Спринты 0-10 |
| [P1] | Backdating |
| [P2] | Формат номеров |
| [SA] | Просрочки + застывшие дела |
| [SB] | Дашборд по ролям |
| [SC] | Фильтр по офису + импорт НП |
| [BUG] | Баг-репорт |
| [DB] | Изменение модели / миграция |
| [DOC4]-[DOC8] | Документы 4-8 |

## Обязательная первая строка промпта
```
Не запускай команды. Только создай/измени файлы.
```

## Шаблоны промптов

### Новая фича
```
[DB] Добавь в модель DeliveryRecord поле:
proof_file = FileField(upload_to='delivery/proofs/%Y/%m/', null=True, blank=True)

Создай миграцию. Обнови только models.py.
Не трогай views и шаблоны.
```

### Баг
```
[BUG] apps/delivery/views.py строка ~47
Ошибка: [текст ошибки]
Контекст: пользователь нажал кнопку "Зафиксировать"
Не трогай другие файлы.
```

### Изменение шаблона
```
Задача: добавить поле sent_at в форму вручения.

Файл: templates/delivery/create.html
Добавить перед блоком {# Примечание #}:
[HTML код]

Не трогай другие файлы.
```

### После 2 неудачных попыток
```
/clear
```
Затем переформулировать с более конкретным описанием.

## Правила написания промптов
1. Один промпт = одна задача
2. Указывай конкретный файл и строку
3. Пиши "Не трогай другие файлы" если нужно ограничить scope
4. При изменении модели — всегда упоминай про миграцию
5. Ссылайся на существующий паттерн: "сделай по образцу AllowBackdatingView"
