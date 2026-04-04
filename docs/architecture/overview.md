# АППК — Архитектура системы

## Обзор
Веб-система автоматизации административных дел для КГД РК.
Сервер: http://91.243.71.139
Репозиторий: https://github.com/kuanqk/KGD_APPK.git

## Стек
- Backend: Python 3.11, Django 4.2, PostgreSQL 15
- Очереди: Celery + Redis
- Frontend: Django Templates (server-side rendering)
- Инфра: Docker Compose (web, db, redis, worker, backup)
- PDF: xhtml2pdf + DejaVu шрифт (кириллица)
- Excel: openpyxl

## Сервисы Docker
| Сервис | Образ | Назначение |
|--------|-------|-----------|
| web | custom (gunicorn) | Django-приложение, 3 воркера |
| db | postgres:15-alpine | База данных |
| redis | redis:7-alpine | Брокер Celery + кэш |
| worker | custom (celery) | Фоновые задачи |
| backup | postgres:15-alpine | Бэкап БД в 02:00 |

## Celery Beat расписание
| Задача | Расписание | Описание |
|--------|-----------|----------|
| check_deadlines | Каждый час | Уведомления о протоколах |
| send_pending_emails | Каждые 30 мин | Email-рассылка |
| check_stagnant_cases | 09:00 ежедневно | Застывшие дела |

## Приложения
```
apps/
├── accounts/      # User, роли, аутентификация
├── cases/         # AdministrativeCase, Taxpayer, справочники
├── documents/     # CaseDocument, шаблоны, генерация PDF
├── delivery/      # DeliveryRecord, трекинг вручения
├── hearings/      # Hearing, HearingProtocol
├── decisions/     # FinalDecision (прекращение / проверка)
├── approvals/     # ApprovalFlow (согласование)
├── notifications/ # Notification + Celery tasks
├── audit/         # AuditLog (иммутабельный лог)
├── reports/       # PDF/XLSX экспорт
└── feedback/      # Обратная связь пользователей
```

## Шаблоны
Все HTML-шаблоны в `templates/` в корне проекта (не внутри приложений).
Структура: `templates/cases/`, `templates/delivery/`, и т.д.

## Формат номеров
```
Дела:      АД-КОД-YYYYMMDD-NNNNNNN   пример: АД-01-20260317-0000001
Документы: ИЗВ-КОД-YYYYMMDD-NNNNNNN  пример: ИЗВ-01-20260317-0000001
```
Префиксы документов: `ИЗВ` · `ПРД` · `АКТ` · `ДЭР` · `ПРТ` · `ПРК` · `ВНП`

Последовательность хранится в `Department.doc_sequence + Department.seq_year`.
Обновление атомарно через `select_for_update()`.
