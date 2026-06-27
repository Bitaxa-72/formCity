# Схема отчета `Модель`

## Назначение

`model` хранит финансовую модель проекта и отвечает на запросы по верхнеуровневым KPI.

Сейчас в пользовательских ответах подключены публичный KPI-слой и безопасный raw-слой исходных листов.

## Источники

```text
оригиналы таблиц/модель
```

Импортер: `app/importers/model.py`.

Проект по умолчанию: `obvodny`.

Если период не указан, backend берет последний доступный срез модели и в ответе пишет, что это последний актуальный срез.

## Таблицы

### `model_sources`

Реестр загруженных файлов модели.

Ключевые поля:

```text
project
snapshot_month
file_name
file_hash
imported_at
```

### `model_monthly_facts`

Помесячные строки модели из листов `ФМ_` и `ФМ_ПЛАН`.

Ключевые поля:

```text
project
snapshot_month
scenario
period_month
period_status
row_code
section
metric_name
metric_key
value
normalized_value
unit
is_sensitive
sensitive_kind
source_sheet
source_row
source_col
source_file
```

### `model_kpi_facts`

KPI из листов `NEWKPI's_` и `NEWKPI's_ПЛАН`.

Ключевые поля:

```text
project
snapshot_month
scenario
section
metric_name
metric_key
value
normalized_value
unit
is_sensitive
sensitive_kind
source_sheet
source_row
source_col
source_file
```

### `model_comparison_facts`

Показатели листа `Сравнение`.

Ключевые поля:

```text
project
snapshot_month
section
metric_name
metric_key
current_value
plan_value
deviation_value
deviation_percent
unit
is_sensitive
sensitive_kind
source_sheet
source_row
source_file
```

### `model_passport_facts`

Паспортные и справочные строки листа `Паспорт`.

Важно: эта таблица может содержать чувствительные данные. Такие строки не должны попадать в пользовательский ответ.

Ключевые поля:

```text
project
snapshot_month
section
metric_name
metric_key
value_text
value_number
unit
is_sensitive
sensitive_kind
source_sheet
source_row
source_col
source_file
```

### `model_assumption_facts`

Допущения и проценты из листа `Проценты`.

Ключевые поля:

```text
project
snapshot_month
section
metric_name
metric_key
value
unit
is_sensitive
sensitive_kind
source_sheet
source_row
source_col
source_file
```

## Raw-слой

Raw-слой нужен, чтобы сохранить исходные листы без потери информации и дать пользователю доступ к безопасным строкам без контактов и номеров документов.

Импортируются листы:

```text
Для консолидации -> consolidation
Финмодель -> financial_model
Остатки -> remains
```

### `model_raw_sheets`

Описание raw-листа.

```text
project
snapshot_month
source_file
sheet_name
sheet_kind
max_row
max_column
row_count
cell_count
```

### `model_raw_rows`

Непустые строки raw-листа.

```text
project
snapshot_month
source_file
sheet_name
sheet_kind
row_number
row_label
non_empty_cells
raw_values
is_sensitive
sensitive_kind
```

### `model_raw_cells`

Непустые ячейки raw-листа.

```text
project
snapshot_month
source_file
sheet_name
sheet_kind
row_number
column_number
column_letter
value_type
value_text
value_number
value_date
value_bool
is_sensitive
sensitive_kind
```

## Публичные ключи

```text
model_revenue - выручка
model_cost_of_sales - себестоимость продаж
model_gross_profit - валовая прибыль
model_net_profit - чистая прибыль
model_npv - NPV
model_roe - ROE
model_llcr - LLCR
model_total_area - общая площадь
model_units_count - количество помещений
model_pir - ПИР
```

## Поддерживаемые запросы

```text
модель
модель апрель
модель выручка апрель
модель NPV
модель ROE март
какие показатели есть в модели?
какие срезы есть в модели?
какие листы есть в модели?
модель финмодель апрель
модель остатки апрель
модель найди общая площадь в финмодели апрель
```

## Развилки

### Нет периода

Backend берет последний доступный `snapshot_month`.

Ответ должен явно писать:

```text
Период: последний актуальный срез, апрель 2026
```

### Есть период

Период трактуется как срез модели, а не как диапазон календарных месяцев.

### Нет метрики

Используется сводка:

```text
model_revenue
model_cost_of_sales
model_gross_profit
model_net_profit
model_npv
```

### Запрошен список

`dimension_query` возвращает:

```text
metric - доступные показатели
snapshot_month - доступные срезы
```

### Запрошена чувствительная информация

Backend не выводит контакты, ФИО, номера документов, паспортные и документные данные.

### Запрошен raw-слой

Данные raw-слоя доступны через view:

```text
model_raw_sheets - список raw-листов модели
model_raw_rows - строки выбранного raw-листа
model_raw_search - поиск по безопасным raw-строкам и ячейкам
```

Поддерживаемые фильтры:

```text
raw_sheet - Для консолидации / Финмодель / Остатки
raw_query - поисковая строка
```

В ответ не попадают строки и ячейки, помеченные как чувствительные.

## SQL-слой

Публичные KPI читаются через объединенный SQL-слой:

```text
model_kpi_facts
model_comparison_facts
model_passport_facts
```

В выборку попадают только строки:

```text
is_sensitive = 0
```

Raw-таблицы не участвуют в KPI-агрегаторе `MODEL_SQL_TEMPLATE`. Для них используется отдельная безопасная SQL-ветка.
