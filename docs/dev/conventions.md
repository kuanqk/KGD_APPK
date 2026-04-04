# Соглашения по коду

## Модели
- Всегда: `verbose_name`, `ordering`, `__str__`
- Статусы только через `TextChoices`, никогда не хардкодить строки
- `db_index=True` для полей по которым фильтруем

## Views
- Только class-based views
- `LoginRequiredMixin` первым в цепочке наследования
- Бизнес-логика только в `services.py`, не во views

## URL-имена
```python
app_name = "cases"
# Формат: app:action
# Использование в шаблоне:
{% url 'cases:detail' pk=case.pk %}
```

## Сервисный слой
```python
# apps/cases/services.py
# Вся бизнес-логика здесь
def create_case(operator, taxpayer_data, basis) -> AdministrativeCase:
    ...
    audit_log(operator, "case_created", "case", case.id, {...})
    return case
```

## Аудит — обязательно после каждой мутации
```python
from apps.audit.services import audit_log

audit_log(
    user=request.user,
    action="status_changed",
    entity_type="case",
    entity_id=case.id,
    details={"from": old_status, "to": new_status}
)
```

## QuerySet — всегда фильтровать по пользователю
```python
# Во view:
def get_queryset(self):
    return AdministrativeCase.objects.for_user(self.request.user)

# Запрещено:
AdministrativeCase.objects.all()  # утечка данных между ролями
```

## Celery-задачи
```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def my_task(self, case_id):
    try:
        ...
    except Exception as exc:
        raise self.retry(exc=exc)
```

## Шаблоны
Все в `templates/` в корне проекта (не внутри приложений).
Структура: `templates/cases/`, `templates/delivery/`, и т.д.

## Миграции
```bash
# Перед коммитом всегда проверять:
python manage.py makemigrations --check

# При конфликте веток:
docker compose run --rm web python manage.py makemigrations --merge --no-input
```

## Запрещено
| Запрет | Причина |
|--------|---------|
| Бизнес-логика во views | Не тестируется, дублируется |
| `objects.all()` без `for_user()` | Утечка данных |
| Удаление signed документов | ТЗ запрещает |
| `print()` | Только `logging.getLogger(__name__)` |
| Хардкод статусов строками | Только TextChoices |
| `\n` в Celery задачах | Вместо них отдельные Paragraph |
