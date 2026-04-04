# АППК — Project Context (архив для промптов)

> **Актуальная документация** (при расхождении приоритет у них и кода):  
> [`docs/handoff.md`](../handoff.md) · [`docs/README.md`](../README.md) · [`docs/dev/onboarding.md`](../dev/onboarding.md) · [`docs/apps/`](../apps/)  
> Этот файл — сжатый контекст для Claude Code; исторические спринты и шорткоды: [`sprints.md`](sprints.md), [`rules.md`](rules.md).

## What & Why

Web platform for administrative case management in Kazakhstan tax authorities (КГД РК).

Automates: notice creation → document delivery → mail returns → hearings → case termination or tax audit initiation.

## Stack

- Backend: Python 3.11, Django 4.2, PostgreSQL 15
- Queue: Celery + Redis; **Celery Beat** в отдельном сервисе `beat` (`docker-compose.yml`)
- Frontend: Django Templates (server-side)
- Infra: Docker Compose — `web`, `db`, `redis`, `worker`, `beat`, `backup`
- PDF: xhtml2pdf + DejaVu; Excel: openpyxl

Локально приложение слушает **порт 8000** (`http://localhost:8000/`). Отдельный Nginx в этом compose не обязателен; на проде может стоять перед приложением.

## Project structure

```
KGD_APPK/
├── config/settings/{base,dev,prod}.py
├── apps/
│   ├── accounts/    # User, roles, department
│   ├── cases/       # AdministrativeCase, Taxpayer, Department, …
│   ├── documents/   # CaseDocument, templates, PDF
│   ├── delivery/    # DeliveryRecord
│   ├── hearings/    # Hearing, HearingProtocol
│   ├── decisions/   # FinalDecision
│   ├── approvals/   # ApprovalFlow
│   ├── notifications/ # Notification + Celery tasks
│   ├── audit/       # AuditLog
│   ├── reports/       # PDF/XLSX
│   └── feedback/    # Pilot feedback
└── templates/       # все HTML в корне, не внутри apps
```

## Core business flow

```
Notice → Preliminary Decision → Deliver to Taxpayer
  ├─ Delivered: Schedule Hearing → Protocol → [Terminate | Tax Audit]
  └─ Returned: Inspection Act + ДЭР Request → then Hearing path
```

## Hard rules (never break)

1. Final decision requires hearing protocol — block otherwise.
2. After protocol: **2 working days** deadline (`check_deadlines`, Celery).
3. Termination only with valid basis.
4. Documents in final/signed status → **no delete**, new version only.
5. User-facing mutations → `AuditLog` where applicable; background jobs should not skip audit rules defined for the domain.
6. Data isolation — `AdministrativeCase.objects.for_user(user)` (see below).

## User roles

`admin` | `operator` | `reviewer` | `executor` | `observer`

Отдельно от ролей: **наблюдатели по делу** (`case_observers` M2M) — видят дело, не создают документы.

### CaseQuerySet.for_user() — текущая логика

```python
from django.db.models import Q

def for_user(self, user):
    if user.role in ("admin", "reviewer"):
        return self
    if user.role == "executor":
        return self.filter(
            Q(responsible_user=user) | Q(case_observers=user)
        ).distinct()
    if user.department_id:
        return self.filter(
            Q(department=user.department) | Q(case_observers=user)
        ).distinct()
    if user.region:
        return self.filter(
            Q(region__name=user.region) | Q(case_observers=user)
        ).distinct()
    return self.filter(case_observers=user).distinct()
```

Источник: `apps/cases/models.py`, подробнее [`docs/apps/cases.md`](../apps/cases.md).

## Code conventions

- **Models**: `verbose_name`, `ordering`, `__str__`; statuses via `TextChoices`.
- **Views**: class-based; `LoginRequiredMixin` first; optional `PermissionRequiredMixin` / `UserPassesTestMixin` after.
- **Business logic**: in `services.py`, not in views.
- **URLs**: `app_name = "cases"` → `{% url 'cases:detail' pk=case.pk %}`.
- **Audit**: `audit_log(...)` after mutations from HTTP; same discipline for tasks where required.
- **QuerySets**: never `objects.all()` for case lists without `for_user()`.
- **Celery**: `@shared_task(bind=True, max_retries=3, default_retry_delay=60)`; no `print()` — use `logging`.
- **Templates**: under `templates/` in repo root.

## Key models (quick ref)

`AdministrativeCase` · `Taxpayer` · `CaseDocument` · `DeliveryRecord` · `Hearing` · `HearingProtocol` · `FinalDecision` · `ApprovalFlow` · `AuditLog` · `Department` · `StagnationSettings`

### Department (`apps/cases/models.py`)

```python
class Department(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=2, unique=True)  # «01»…«20»
    doc_sequence = models.PositiveIntegerField(default=0)
    seq_year = models.IntegerField(default=0)
    case_sequence = models.PositiveIntegerField(default=0)
    case_seq_year = models.IntegerField(default=0)
```

Используется для изоляции по офису и генерации номеров дел/документов.

### StagnationSettings

Singleton (`pk=1`). `StagnationSettings.get()` — доступ. Поля: `stagnation_days`, `notify_reviewer`.

### AdministrativeCase — поля (фрагмент)

```python
department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
last_activity_at = models.DateTimeField(auto_now_add=True, db_index=True)  # также обновляется в change_case_status()
allow_backdating = models.BooleanField(default=False)
backdating_allowed_by = models.ForeignKey(User, null=True, blank=True, ...)
backdating_allowed_at = models.DateTimeField(null=True, blank=True)
backdating_comment = models.TextField(blank=True)
case_observers = models.ManyToManyField(User, ...)
```

## Номера документов

Новый формат (дело с офисом):

```
PREFIX-КОД-YYYYMMDD-NNNNNNN
Пример: ИЗВ-05-20260316-0000042
```

Префиксы: `ИЗВ` · `ПРД` · `АКТ` · `ДЭР` · `ПРТ` · `ПРК` · `ВНП`

Старый формат `PREFIX-ГГГГ-NNNNN` — для дел без офиса.

Последовательность документов: `Department.doc_sequence` + `Department.seq_year`; номера дел: `case_sequence` + `case_seq_year`. Обновление атомарно через `select_for_update()`.

## Типы документов (порядок как в `docs/handoff.md`)

1. Извещение о явке  
2. Предварительное решение  
3. Протокол заслушивания  
4. Акт налогового обследования  
5. Запрос в ДЭР  
6. Решение о прекращении дела  
7. Инициирование внеплановой проверки  
8. Приказ о назначении проверки  

Кодовые имена см. `DocumentType` в [`docs/architecture/models.md`](../architecture/models.md).

## Dev commands

```bash
make up
make migrate
make test
docker compose exec web python manage.py makemigrations --check
```

## Reference files

| Назначение | Путь |
|------------|------|
| Актуальный handoff | [`docs/handoff.md`](../handoff.md) |
| Обзор продукта | [`docs/README.md`](../README.md) |
| Онбординг | [`docs/dev/onboarding.md`](../dev/onboarding.md) |
| Модели | [`docs/architecture/models.md`](../architecture/models.md) |
| Архив спринтов | [`docs/archive/sprints.md`](sprints.md) |
| Шорткоды | [`docs/archive/rules.md`](rules.md) |

## Sprint shortcodes (prompts)

`[S0]`…`[S10]` — см. [`sprints.md`](sprints.md).  
`[P1]` Backdating · `[P2]` Doc numbers · `[SA]` Stagnation · `[SB]` Dashboard · `[SC]` Office filter + import
