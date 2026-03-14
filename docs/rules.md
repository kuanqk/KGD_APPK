# rules.md — Правила разработки АППК

> Цель: экономия токенов, ускорение итераций, единый стиль кода.

---

## 1. Как общаться с Claude

### Давай контекст минимально, но точно

```
# ХОРОШО
"Sprint 3. Модель DeliveryRecord уже есть. Добавь view для регистрации возврата письма."

# ПЛОХО
"Я делаю проект АППК, это система автоматизации административных дел... [500 слов]"
```

- Всегда указывай **текущий Sprint**
- Называй **конкретный файл/модуль** если он уже существует
- Описывай **что уже сделано**, а не весь проект заново

### Форматы запросов

| Задача | Формат |
|--------|--------|
| Новая модель | "Создай модель X с полями: a, b, c. FK → Y" |
| View | "View для [действие], роли: [роли], метод: GET/POST" |
| Баг | "Ошибка: [текст]. Файл: [путь]. Строка: [N]" |
| Рефакторинг | "Рефактор [функция] — убери дублирование, не меняй логику" |

---

## 2. Структура проекта

```
appk/
├── config/              # settings, urls, wsgi, asgi
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
├── apps/
│   ├── accounts/        # User, Role, права
│   ├── cases/           # AdministrativeCase, Taxpayer
│   ├── documents/       # CaseDocument, шаблоны
│   ├── delivery/        # DeliveryRecord
│   ├── hearings/        # Hearing, HearingProtocol
│   ├── decisions/       # FinalDecision
│   ├── approvals/       # ApprovalFlow
│   ├── notifications/   # Notification
│   ├── audit/           # AuditLog
│   └── reports/         # отчёты, экспорт
├── templates/
├── static/
├── docker/
└── manage.py
```

---

## 3. Соглашения по коду

### Модели

```python
# Всегда: verbose_name, ordering, __str__
class AdministrativeCase(models.Model):
    case_number = models.CharField(max_length=20, unique=True, verbose_name="Номер дела")
    status = models.CharField(max_length=50, choices=CaseStatus.choices, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Административное дело"
        verbose_name_plural = "Административные дела"
        ordering = ["-created_at"]

    def __str__(self):
        return self.case_number
```

### Views — только class-based

```python
# LoginRequiredMixin + PermissionMixin всегда первые
class CaseListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "cases.view_administrativecase"
    model = AdministrativeCase
    template_name = "cases/list.html"
    paginate_by = 25
```

### URL-имена — формат: `app:action`

```python
# cases/urls.py
app_name = "cases"
urlpatterns = [
    path("", CaseListView.as_view(), name="list"),
    path("<int:pk>/", CaseDetailView.as_view(), name="detail"),
    path("create/", CaseCreateView.as_view(), name="create"),
]
# Использование: {% url 'cases:detail' pk=case.pk %}
```

### Сервисный слой

```python
# Бизнес-логика → в services.py, НЕ во views
# apps/cases/services.py
def create_case(operator, taxpayer_data, basis) -> AdministrativeCase:
    ...
    audit_log(operator, "case_created", case)
    return case
```

### Статусы через TextChoices

```python
class CaseStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    NOTICE_CREATED = "notice_created", "Извещение создано"
    TERMINATED = "terminated", "Прекращено"
    COMPLETED = "completed", "Завершено"
```

---

## 4. Аудит — обязательно везде

```python
# Всегда логировать через единую функцию
from apps.audit.services import audit_log

audit_log(
    user=request.user,
    action="status_changed",       # snake_case константа
    entity_type="case",
    entity_id=case.id,
    details={"from": old_status, "to": new_status}
)
```

---

## 5. Разграничение доступа

```python
# QuerySet всегда фильтруем по пользователю
class CaseQuerySet(models.QuerySet):
    def for_user(self, user):
        if user.role == "observer":
            return self.filter(region=user.region)
        if user.role == "executor":
            return self.filter(responsible_user=user)
        return self  # admin, operator, reviewer — всё

# Во view:
def get_queryset(self):
    return AdministrativeCase.objects.for_user(self.request.user)
```

---

## 6. Шаблоны документов

```python
# Подстановка через context_dict из карточки дела
# НЕ дублировать логику — один метод на всё
def get_document_context(case: AdministrativeCase) -> dict:
    return {
        "case_number": case.case_number,
        "taxpayer_name": case.taxpayer.name,
        "taxpayer_iin": case.taxpayer.iin_bin,
        "date_today": date.today().strftime("%d.%m.%Y"),
        ...
    }
```

---

## 7. Celery-задачи

```python
# tasks.py — только в apps/notifications/
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_deadline_approaching(self, case_id):
    try:
        ...
    except Exception as exc:
        raise self.retry(exc=exc)
```

---

## 8. Что НЕ делать

| Запрет | Причина |
|--------|---------|
| Бизнес-логика во views | Не тестируется, дублируется |
| `objects.all()` без фильтра по пользователю | Утечка данных между ролями |
| Прямое удаление финальных документов | ТЗ запрещает, нужна новая версия |
| `print()` для отладки | Только `logger = logging.getLogger(__name__)` |
| Хардкод статусов строками | Только через `TextChoices` |
| Миграции без `--check` | Сломает прод |

---

## 9. Команды разработки

```bash
# Запуск
make up

# Миграции
make migrate
python manage.py makemigrations --check  # проверить перед коммитом

# Тесты
make test
python manage.py test apps.cases --verbosity=2

# Celery (локально)
celery -A config worker -l info
celery -A config beat -l info

# Shell
python manage.py shell_plus  # django-extensions
```

---

## 10. Шорткоды для запросов к Claude

Используй в начале запроса для экономии контекста:

| Код | Значение |
|-----|----------|
| `[S1]` | Sprint 1 (Реестр дел) |
| `[S2]` | Sprint 2 (Документы) |
| `[S3]` | Sprint 3 (Вручение) |
| `[S4]` | Sprint 4 (Возврат) |
| `[S5]` | Sprint 5 (Заслушивание) |
| `[S6]` | Sprint 6 (Решения) |
| `[S7]` | Sprint 7 (Согласование) |
| `[S8]` | Sprint 8 (Уведомления) |
| `[S9]` | Sprint 9 (Отчёты) |
| `[BUG]` | Баг-репорт |
| `[REF]` | Рефакторинг |
| `[DB]` | Изменение модели/миграция |

**Пример:** `[S3][DB] Добавь поле tracking_number в DeliveryRecord, тип CharField(100), nullable`
