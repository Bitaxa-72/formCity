# Сводный отчет

Отчет `summary` подготовлен на уровне БД, импорта данных и backend-ответов в Telegram. В бот подключен безопасный агрегатный слой: обзор файлов, листов, строк, ячеек, типов листов, колонок и суммы по безопасным числовым колонкам.

## Источник

Папка: `оригиналы таблиц/сводная`

Файлы:
- `велл московский/Сводная_Велл Московский.xlsx`
- `евгеньевский/ЖК Евгеньевский.xlsx`
- `обводный/Сводная_Обводный 118.xlsx`

Проекты определяются автоматически:
- `moskovsky`
- `evgenievsky`
- `obvodny`

## Почему схема универсальная

Сводные файлы сильно отличаются по листам и колонкам. Поэтому данные уложены в универсальную структуру:
- источник;
- лист;
- строка;
- непустая ячейка.

Так в БД попадает весь объем данных без потерь, а backend-логика может поверх этой базы строить безопасные агрегаты и будущие предметные резолверы по площадям, выручке, оплатам, остаткам, классам, этажам, датам и другим полям.

## Таблицы

### `summary_sources`

Файлы-источники.

Ключевые поля:
- `project`
- `file_name`
- `file_hash`

### `summary_sheets`

Листы внутри файлов.

Ключевые поля:
- `project`
- `source_file`
- `sheet_name`
- `sheet_kind`
- `header_row`
- `max_row`
- `max_column`
- `row_count`
- `cell_count`

Типы `sheet_kind`:
- `residential_units` - апартаменты/квартиры
- `commercial_units` - коммерция
- `storage_units` - кладовки
- `contract_termination` - расторжения ДДУ
- `assignment` - уступки
- `guaranteed_income` - гарантированный доход/аренда
- `timeline` - данные по датам
- `class_summary` - отчет по классам
- `summary_totals` - итоговая сводная
- `sale_purchase_contract` - ДКП
- `window_agreements` - ДС по окнам
- `agents` - агенты
- `generic` - прочий лист

### `summary_rows`

Непустые строки листов.

Ключевые поля:
- `project`
- `source_file`
- `sheet_name`
- `sheet_kind`
- `row_number`
- `row_type`
- `row_label`
- `period_label`
- `unit_number`
- `customer_name`
- `raw_values`
- `is_sensitive`
- `sensitive_fields`

Типы `row_type`:
- `header` - строка заголовка или строки выше заголовка
- `period_group` - строка периода
- `group` - группирующая строка
- `detail` - обычная строка данных

### `summary_cells`

Все непустые ячейки.

Ключевые поля:
- `project`
- `source_file`
- `sheet_name`
- `sheet_kind`
- `row_number`
- `column_number`
- `column_letter`
- `header_label`
- `header_key`
- `value_type`
- `value_text`
- `value_number`
- `value_date`
- `value_bool`
- `is_sensitive`

`header_key` - нормализованный ключ колонки. Например:
- `фио_клиента`
- `площадь`
- `цена_дду`
- `оплачено`
- `остаток`
- `дата_дду`

## Backend-слой

Подключенные метрики:
- `summary_sheet_count` - количество листов;
- `summary_row_count` - количество строк;
- `summary_cell_count` - количество ячеек;
- `summary_numeric_cell_count` - количество числовых ячеек;
- `summary_value_sum` - сумма безопасных числовых значений.

Подключенные представления:
- `summary_overview` - общий безопасный обзор;
- `summary_values` - безопасные числовые значения по выбранной колонке;
- `summary_available_projects` - доступные проекты;
- `summary_available_files` - доступные файлы;
- `summary_available_sheets` - доступные листы;
- `summary_available_sheet_kinds` - доступные типы листов;
- `summary_available_headers` - доступные безопасные колонки;
- `summary_available_row_types` - типы строк.

Поддержанные фильтры и группировки:
- `project`;
- `source_file`;
- `sheet_name`;
- `sheet_kind`;
- `row_type`;
- `header_key`;
- `header_key_contains`;
- `header_label_contains`.

Если проект не указан, результаты группируются по проектам отдельно. Период для сводного отчета не применяется: в ответе используется весь доступный объем сводных таблиц.

## Безопасность

В сводных таблицах есть ФИО, номера договоров, менеджеры, агенты, примечания и договорные данные.

Импортер помечает чувствительные ячейки через `is_sensitive = true`, если заголовок содержит:
- ФИО;
- клиент;
- агент;
- менеджер;
- ДДУ;
- договор;
- ДКП;
- бронь;
- примечание;
- контакт.

Эти данные можно использовать для фильтров и расчетов, но нельзя напрямую выводить пользователю в Telegram. Для ответов нужны агрегаты, суммы, количества и обезличенные распределения.
