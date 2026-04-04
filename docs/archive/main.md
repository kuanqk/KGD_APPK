# АППК — Project Context for Claude Code

## What & Why
Web platform for administrative case management in Kazakhstan tax authorities (КГД).
Automates: notice creation → document delivery → mail returns → hearings → case termination or tax audit initiation.

## Stack
- Backend: Python 3.11, Django 4.x, PostgreSQL 15
- Queue: Celery + Redis
- Frontend: Django Templates (MVP)
- Infra: Docker Compose (web, db, redis, worker, nginx)

## Project Structure
```
appk/
├── config/settings/{base,dev,prod}.py
└── apps/
    ├── accounts/    # User, roles, permissions
    ├── cases/       # AdministrativeCase, Taxpayer
    ├── documents/   # CaseDocument, templates, generation
    ├── delivery/    # DeliveryRecord, delivery tracking
    ├── hearings/    # Hearing, HearingProtocol
    ├── decisions/   # FinalDecision (terminate or audit)
    ├── approvals/   # ApprovalFlow
    ├── notifications/ # Notification + Celery tasks
    ├── audit/       # AuditLog (log everything)
    └── reports/     # PDF/XLSX export
```

## Core Business Flow
```
Notice → Preliminary Decision → Deliver to Taxpayer
  ├─ Delivered: Schedule Hearing → Protocol → [Terminate | Tax Audit]
  └─ Returned: Inspection Act + ДЭР Request → then Hearing path
```

## Hard Rules (never break these)
1. Final decision requires hearing protocol — block it otherwise
2. After protocol: track **2 working days** deadline (Celery task)
3. Termination only with valid basis (violations not confirmed / self-corrected)
4. Documents in final status → **no delete**, create new version only
5. All user actions → `AuditLog` (always)
6. Data isolation by role — filter querysets via `queryset.for_user(user)`

## 5 User Roles
`admin` | `operator` | `reviewer` | `executor` | `observer`
Observer sees own region only. Reviewer approves/rejects. No others delete final docs.

### CaseQuerySet.for_user() — текущая логика
```python
def for_user(self, user):
    if user.role in ("admin", "reviewer"):
        return self                          # все дела
    if user.role == "executor":
        return self.filter(responsible_user=user)
    # operator, observer — по офису; fallback на регион
    if user.department_id:
        return self.filter(department=user.department)
    if user.region:
        return self.filter(region=user.region)
    return self.none()
```

## Code Conventions
- **Models**: always `verbose_name`, `ordering`, `__str__`
- **Views**: class-based, `LoginRequiredMixin` + `PermissionRequiredMixin` first
- **URLs**: `app_name = "cases"` → `name="list|detail|create"`
- **Business logic**: in `services.py`, never in views
- **Statuses**: `TextChoices` only, never hardcoded strings
- **Audit**: call `audit_log(user, action, entity_type, entity_id, details)` after every mutation
- **Celery tasks**: `bind=True, max_retries=3` always
- **No** `print()` — use `logging.getLogger(__name__)`
- **No** `objects.all()` without user filter

## Key Models (quick ref)
`AdministrativeCase` · `Taxpayer` · `CaseDocument` · `DeliveryRecord`
`Hearing` · `HearingProtocol` · `FinalDecision` · `ApprovalFlow` · `AuditLog`
`Department` · `StagnationSettings`

### Department (apps/cases/models.py)
```python
class Department(models.Model):
    name = models.CharField(max_length=200)         # «Управление №5»
    code = models.CharField(max_length=2, unique=True)  # «05»
    doc_sequence = models.PositiveIntegerField(default=0)  # текущий порядковый № документа
    seq_year = models.IntegerField(default=0)       # год текущей последовательности
```
Используется для: изоляции данных по офису, генерации номеров документов.

### StagnationSettings (apps/cases/models.py)
Синглтон (pk=1). Доступ через `StagnationSettings.get()`.
```python
class StagnationSettings(models.Model):
    stagnation_days = models.PositiveIntegerField(default=30)
    notify_reviewer = models.BooleanField(default=True)
```

### AdministrativeCase — новые поля
```python
department = models.ForeignKey(Department, null=True, blank=True, on_delete=SET_NULL)
last_activity_at = models.DateTimeField(auto_now_add=True, db_index=True)  # обновляется при change_case_status()
allow_backdating = models.BooleanField(default=False)
backdating_allowed_by = models.ForeignKey(User, null=True, blank=True, ...)
backdating_allowed_at = models.DateTimeField(null=True, blank=True)
backdating_comment = models.TextField(blank=True)
```

## Формат номеров документов
Новый формат (для дел с офисом):
```
PREFIX-КОД-YYYYMMDD-NNNNNNN
Пример: ИЗВ-05-20260316-0000042
```
Префиксы: `ИЗВ` · `ПРД` · `АКТ` · `ДЭР` · `ПРТ` · `ПРК` · `ВНП`

Старый формат `PREFIX-ГГГГ-NNNNN` — для дел без офиса (обратная совместимость).

Последовательность хранится в `Department.doc_sequence` + `Department.seq_year`.
Обновление атомарно через `select_for_update()`.

## Document Templates (8 types)
1. Извещение о явке
2. Предварительное решение
3. Акт налогового обследования
4. Запрос в ДЭР
5. Протокол заслушивания
6. Решение о прекращении
7. Инициирование внеплановой проверки
8. Приказ о назначении проверки

## Dev Commands
```bash
make up          # docker compose up
make migrate     # apply migrations
make test        # run tests
python manage.py makemigrations --check  # before every commit
```

## Reference Files
- `docs/claude.md`   — full domain model, all statuses, business rules
- `docs/sprints.md`  — 11 sprints, acceptance criteria per sprint
- `docs/rules.md`    — shortcodes [S1]-[S10], [BUG], [REF], [DB]

## Sprint Shortcodes (use in prompts to save tokens)
`[S0]`=Infra `[S1]`=Cases `[S2]`=Docs `[S3]`=Delivery `[S4]`=Return
`[S5]`=Hearing `[S6]`=Decisions `[S7]`=Approvals `[S8]`=Notifications
`[S9]`=Reports `[S10]`=Security
`[P1]`=Backdating `[P2]`=DocNumbers `[SA]`=Stagnation `[SB]`=Dashboard `[SC]`=OfficeFilter+Import
