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
