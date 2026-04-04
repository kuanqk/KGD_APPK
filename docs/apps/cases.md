# App: cases

## Назначение
Ядро системы. Управляет жизненным циклом административных дел, налогоплательщиками и справочниками.

## Ключевые файлы
- `models.py` — AdministrativeCase, Taxpayer, Department, справочники
- `services.py` — create_case, change_case_status, allow_backdating
- `validators.py` — KZValidator (ИИН/БИН, телефон)
- `views.py` — CaseListView, CaseDetailView, CaseCreateView, UpdateObserversView, справочники
- `forms.py` — CaseCreateForm, CaseFilterForm, TaxAuthorityDetailsForm

## Минимальный контекст для задач по этому app
```
Передавай в Claude Code:
- docs/apps/cases.md (этот файл)
- apps/cases/models.py
- apps/cases/services.py (если задача про бизнес-логику)
- apps/cases/views.py (если задача про views)
```

## Изоляция данных (for_user)
```python
def for_user(self, user):
    if user.role in ("admin", "reviewer"):
        return self  # все дела
    if user.role == "executor":
        return self.filter(
            Q(responsible_user=user) | Q(case_observers=user)
        ).distinct()
    # operator, observer — по офису + наблюдатели
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

## Наблюдатели (case_observers)
M2M → User. Наблюдатели видят дело и документы, но не могут создавать новые документы.
Проверка в `DocumentCreateView.dispatch()` через `case.case_observers.filter(pk=user.pk).exists()`.
Редактируются через модальное окно на карточке дела (admin/operator) — POST на `cases:update_observers`.

## Backdating
`allow_backdating = BooleanField`. Разрешается только admin/reviewer через модальное окно.
Валидация дат в формах документов проверяет это поле + роль пользователя.

## Валидатор ИИН/БИН (KZValidator)
- ИИН: 7-я цифра 1-6 → validate_iin() → извлекает дату рождения + пол
- БИН: всё остальное (включая 7-ю цифру 0) → validate_bin()
- Нестандартная дата регистрации (день=40, месяц=00) → принимается как валидный БИН (reg_date_str=None)
- AJAX-валидация на форме создания дела: /cases/validate-iin/

## basis и category — ManyToMany
Оба поля стали M2M после доработки пилота.
- В форме создания — `CheckboxSelectMultiple`
- На карточке дела — `case.basis_display`, `case.category_display` (property)
- В services.py — `case.basis.set(...)` после `create()`

## Справочники
CRUD + import из Excel для: Region, CaseBasis, CaseCategory, Position, Department, TaxAuthorityDetails.
Общий паттерн view: ListView → CreateView → UpdateView → ToggleView → ImportView.

## Счётчики номеров
`Department.doc_sequence` + `Department.seq_year` для документов.
`Department.case_sequence` + `Department.case_seq_year` для дел.
Обновление атомарно через `select_for_update()` в services.py.
