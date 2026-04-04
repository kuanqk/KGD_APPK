# АППК — URL-маршруты

## accounts (/)
| URL | Имя | Описание |
|-----|-----|---------|
| / | accounts:dashboard | Дашборд |
| /login/ | accounts:login | Вход |
| /logout/ | accounts:logout | Выход |
| /password-change/ | accounts:password_change | Смена пароля |
| /users/ | accounts:user_list | Список пользователей |
| /users/create/ | accounts:user_create | Создать пользователя |
| /users/\<pk\>/edit/ | accounts:user_update | Редактировать |
| /users/\<pk\>/deactivate/ | accounts:user_deactivate | Деактивировать |

## cases (/cases/)
| URL | Имя | Описание |
|-----|-----|---------|
| / | cases:list | Реестр дел |
| /\<pk\>/ | cases:detail | Карточка дела |
| /create/ | cases:create | Создать дело |
| /\<pk\>/allow-backdating/ | cases:allow_backdating | Разрешить backdating (POST) |
| /\<pk\>/update-observers/ | cases:update_observers | Обновить наблюдателей (POST) |
| /taxpayers/import/ | cases:taxpayer_import | Импорт НП из Excel |
| /validate-iin/ | cases:validate_iin | Валидация ИИН/БИН (AJAX) |
| /validate-phone/ | cases:validate_phone | Валидация телефона (AJAX) |
| /references/ | cases:references | Справочники |
| /references/regions/ | cases:region_list | Регионы |
| /references/basis/ | cases:basis_list | Основания |
| /references/categories/ | cases:category_list | Категории |
| /references/positions/ | cases:position_list | Должности |
| /references/departments/ | cases:department_list | Подразделения |
| /references/tax-authority/ | cases:tax_authority_list | Реквизиты КГД |

## documents (/documents/)
| URL | Имя | Описание |
|-----|-----|---------|
| /cases/\<pk\>/documents/create/ | documents:create | Создать документ |
| /cases/\<pk\>/notice/form/ | documents:notice_form | Форма извещения |
| /cases/\<pk\>/preliminary-decision/form/ | documents:preliminary_decision_form | Форма предрешения |
| /cases/\<pk\>/hearing-protocol/form/ | documents:hearing_protocol_form | Форма протокола |
| /cases/\<pk\>/act/create/ | documents:act_create | Акт обследования |
| /cases/\<pk\>/der/create/ | documents:der_create | Запрос в ДЭР |
| /\<pk\>/ | documents:detail | Карточка документа |
| /\<pk\>/download/ | documents:download | Скачать PDF |
| /\<pk\>/print/ | documents:print_preview | Предпросмотр для печати |

## delivery (/delivery/)
| URL | Имя | Описание |
|-----|-----|---------|
| / | delivery:list | Список вручений |
| /cases/\<pk\>/create/ | delivery:create | Создать вручение |
| /\<pk\>/update/ | delivery:update | Зафиксировать результат (возврат) |
| /\<pk\>/update-inline/ | delivery:update_inline | AJAX: чекбокс/дата/файл |

## hearings (/hearings/)
| URL | Имя | Описание |
|-----|-----|---------|
| / | hearings:calendar | Календарь заслушиваний |
| /cases/\<pk\>/schedule/ | hearings:schedule | Назначить заслушивание |
| /\<pk\>/ | hearings:detail | Карточка заслушивания |
| /\<pk\>/complete/ | hearings:complete | Завершить |
| /\<pk\>/protocol/create/ | hearings:protocol_create | Оформить протокол |

## decisions (/decisions/)
| URL | Имя | Описание |
|-----|-----|---------|
| / | decisions:list | Список решений |
| /cases/\<pk\>/terminate/ | decisions:terminate | Прекратить дело |
| /cases/\<pk\>/tax-audit/ | decisions:tax_audit | Назначить проверку |
| /\<pk\>/ | decisions:detail | Карточка решения |
| /\<pk\>/review/ | decisions:review | Согласовать |

## approvals (/approvals/)
| URL | Имя | Описание |
|-----|-----|---------|
| / | approvals:queue | Очередь согласований |
| /\<pk\>/action/ | approvals:action | Рассмотреть |

## прочие
| URL | Имя | Описание |
|-----|-----|---------|
| /notifications/ | notifications:list | Уведомления |
| /reports/ | reports:dashboard | Отчёты |
| /audit/ | audit:list | Лог аудита |
| /feedback/create/ | feedback:create | Обратная связь |
