# АППК — Модели данных

## accounts

### User (AbstractUser)
| Поле | Тип | Описание |
|------|-----|---------|
| role | CharField (TextChoices) | admin/operator/reviewer/executor/observer |
| region | CharField | Регион (устаревшее, заменено на department) |
| phone | CharField | Телефон |
| position | FK → Position | Должность |
| department | FK → Department | Подразделение (офис) |

---

## cases

### Department
| Поле | Тип | Описание |
|------|-----|---------|
| name | CharField | Наименование |
| code | CharField(2) | Код офиса (01-20), unique |
| doc_sequence | PositiveIntegerField | Счётчик документов |
| seq_year | IntegerField | Год счётчика документов |
| case_sequence | PositiveIntegerField | Счётчик дел |
| case_seq_year | IntegerField | Год счётчика дел |

### Taxpayer
| Поле | Тип | Описание |
|------|-----|---------|
| iin_bin | CharField(12) | ИИН/БИН, unique |
| name | CharField(500) | Наименование / ФИО |
| taxpayer_type | CharField (TextChoices) | individual/legal/ie |
| address | TextField | Адрес |
| phone | CharField | Телефон |
| email | EmailField | Email |

### AdministrativeCase
| Поле | Тип | Описание |
|------|-----|---------|
| case_number | CharField(30) | Номер дела, unique |
| status | CharField (CaseStatus) | Текущий статус |
| taxpayer | FK → Taxpayer | Налогоплательщик |
| region | FK → Region | Регион |
| department | FK → Department | Подразделение |
| responsible_user | FK → User | Ответственный |
| case_observers | M2M → User | Наблюдатели (видят, не создают) |
| basis | M2M → CaseBasis | Основания (множественные) |
| category | M2M → CaseCategory | Категории (множественные) |
| description | TextField | Описание |
| allow_backdating | BooleanField | Разрешён ввод задним числом |
| backdating_allowed_by | FK → User | Кто разрешил backdating |
| backdating_allowed_at | DateTimeField | Когда разрешил |
| last_activity_at | DateTimeField | Последняя активность |

**Properties:** `basis_display`, `category_display`

### CaseStatus (TextChoices)
```
draft → notice_created → notice_sent → delivered
  └── mail_returned → act_created → der_sent
hearing_scheduled → hearing_done → protocol_created
  ├── termination_pending → terminated
  └── audit_pending → audit_approved → completed → archived
```

### CaseEvent
Лента событий дела.
event_type: created / status_changed / document_added / assigned / hearing_scheduled / decision_made

### Справочники (cases)
| Модель | Поля |
|--------|------|
| Region | code, name, is_active |
| CaseBasis | code, name, legal_ref, is_active |
| CaseCategory | code, name, is_active |
| Position | name, is_active |
| TaxAuthorityDetails | OneToOne→Department, name, bin_number, address, deputy_name, deputy_position |
| StagnationSettings | синглтон pk=1, stagnation_days (default 30), notify_reviewer |

---

## documents

### DocumentType (TextChoices)
| Значение | Название | Префикс |
|----------|---------|---------|
| notice | Извещение о явке | ИЗВ |
| preliminary_decision | Предварительное решение | ПРД |
| inspection_act | Акт налогового обследования | АКТ |
| der_request | Запрос в ДЭР | ДЭР |
| hearing_protocol | Протокол заслушивания | ПРТ |
| termination_decision | Решение о прекращении | ПРК |
| audit_initiation | Инициирование внеплановой проверки | ВНП |
| audit_order | Приказ о назначении проверки | — |

### CaseDocument
| Поле | Тип | Описание |
|------|-----|---------|
| case | FK → AdministrativeCase | Дело |
| template | FK → DocumentTemplate | Шаблон |
| doc_type | CharField | Тип документа |
| doc_number | CharField(50) | Номер, unique |
| version | PositiveIntegerField | Версия |
| status | CharField | draft/generated/signed/cancelled |
| file_path | CharField | Путь к PDF |
| metadata | JSONField | context_snapshot для печати |

**Правило:** signed документы нельзя удалять, только новая версия.

---

## delivery

### DeliveryRecord
| Поле | Тип | Описание |
|------|-----|---------|
| case_document | FK → CaseDocument | Документ |
| method | CharField | in_person / registered_mail |
| status | CharField | pending / delivered / returned |
| tracking_number | CharField | Трек-номер |
| sent_at | DateTimeField | Дата и время отправки |
| delivered_at | DateTimeField | Дата вручения |
| returned_at | DateTimeField | Дата возврата |
| proof_file | FileField | Файл подтверждения (≤2MB) |
| notes | TextField | Примечание |

---

## hearings

### Hearing
| Поле | Тип | Описание |
|------|-----|---------|
| case | FK → AdministrativeCase | Дело |
| hearing_date | DateField | Дата |
| hearing_time | TimeField | Время |
| location | CharField | Место |
| format | CharField | in_person/remote/mixed |
| status | CharField | scheduled/in_progress/completed/cancelled |
| participants | JSONField | Список участников ["ФИО, должность", ...] |

### HearingProtocol
| Поле | Тип | Описание |
|------|-----|---------|
| hearing | OneToOne → Hearing | Заслушивание |
| protocol_number | CharField | Номер протокола |
| protocol_date | DateField | Дата |
| result_summary | TextField | Краткое содержание |
| file_path | CharField | Путь к файлу протокола |
| signed_protocol_file | FileField | Подписанный протокол НП |
| identity_doc_file | FileField | Удостоверение личности |
| power_of_attorney_file | FileField | Доверенность |
| deadline_2days | DateField | Дедлайн (2 рабочих дня) |

---

## decisions

### FinalDecision
| Поле | Тип | Описание |
|------|-----|---------|
| case | OneToOne → AdministrativeCase | Дело |
| decision_type | CharField | termination / tax_audit |
| status | CharField | draft/pending_approval/approved/rejected |
| basis | CharField (TerminationBasis) | Основание прекращения |
| comment | TextField | Обоснование |
| approver | FK → User | Согласующий |
| approved_at | DateTimeField | Дата согласования |
| rejection_comment | TextField | Комментарий при отклонении |

---

## approvals

### ApprovalFlow
| Поле | Тип | Описание |
|------|-----|---------|
| entity_type | CharField | decision/document/case |
| entity_id | PositiveIntegerField | ID сущности |
| version | PositiveSmallIntegerField | Номер итерации |
| sent_by | FK → User | Направил |
| reviewed_by | FK → User | Рассмотрел |
| result | CharField | pending/approved/rejected/returned |
| comment | TextField | Комментарий рецензента |

---

## notifications

### Notification
| Поле | Тип | Описание |
|------|-----|---------|
| user | FK → User | Получатель |
| case | FK → AdministrativeCase | Дело |
| notification_type | CharField | Тип уведомления |
| message | TextField | Сообщение |
| url | CharField | Ссылка |
| is_read | BooleanField | Прочитано |

Типы: assigned / deadline_soon / overdue / returned / approval_needed / stage_completed / stagnant

---

## audit

### AuditLog
| Поле | Тип | Описание |
|------|-----|---------|
| user | FK → User | Пользователь |
| action | CharField | Действие (snake_case) |
| entity_type | CharField | Тип объекта |
| entity_id | BigIntegerField | ID объекта |
| details | JSONField | Детали |
| ip_address | GenericIPAddressField | IP |
| created_at | DateTimeField | Дата и время |

---

## feedback

### Feedback
| Поле | Тип | Описание |
|------|-----|---------|
| user | FK → User | Пользователь |
| feedback_type | CharField | bug/suggestion/question |
| description | TextField | Описание |
| case_number | CharField | Номер дела (опционально) |
| attachment | FileField | Вложение |
| is_reviewed | BooleanField | Рассмотрено |
| admin_comment | TextField | Комментарий администратора |
