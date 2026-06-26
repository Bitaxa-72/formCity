## Непроектные расходы

Источник: Excel-файлы из папки `оригиналы таблиц/не проектные расходы`.

В импорт берется лист `Лист1`.

## Исходные поля

```text
дата заполнения -> filled_at
в ФМ -> fm_category
Наименование -> item_name
Сумма, руб. -> amount
Исполнено -> executed_amount
Остаток/прогноз -> remaining_amount
Справочно -> reference_text
```

## Таблицы БД

```text
non_project_expense_sources
- project
- period_month
- filled_at
- file_name
- file_hash
- imported_at
```

```text
non_project_expense_facts
- project
- period_month
- filled_at
- row_order
- row_type
- item_kind
- fm_category
- item_name
- amount
- executed_amount
- remaining_amount
- reference_text
- unit
- is_sensitive
- sensitive_kind
- source_sheet
- source_row
- source_file
- created_at
```

## Правила строк

```text
row_type=detail - строка с категорией "в ФМ"
row_type=summary - итоговая или группирующая строка без категории "в ФМ"
```

## Ключи item_kind

```text
lost_income - недополученные доходы
debt_receivable - ДЗ
non_project_expenses_total - итог непроектных расходов
personal - личное
admin_expenses - АХР
evgenievsky - ЕВГ
legal_entity - строки по юрлицам
fit_out - отделочные работы
commercial - коммерческие расходы
furniture - мебелировка
construction - строительные работы
developer_maintenance - содержание застройщика
object_maintenance - содержание объекта и техзаказчик
finance - финансовые расходы
pir - ПИР
other_income_expense - прочие доходы и расходы
other - прочее
```

## Безопасность

Поля `item_name`, `fm_category`, `reference_text` проходят через общий детектор чувствительных данных.

Если строка помечена `is_sensitive=true`, в пользовательский ответ нельзя выводить исходные контактные данные и номера документов. Для расчетов строка может использоваться.

## Импорт

```bash
python -m app.importers.non_project_expenses
```

Или с явным путем:

```bash
python -m app.importers.non_project_expenses --source "../оригиналы таблиц/не проектные расходы"
```
