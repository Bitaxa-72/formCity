# Остатки в продаже

## Назначение

Отчет хранит срез остатков в продаже по проекту `obvodny`.

Исходные файлы:

- `Остатки в продаже_28.02.2026.xlsx`
- `Остатки в продаже_31.03.2026.xlsx`
- `Остатки в продаже_30.04.2026.xlsx`

## Таблицы

### `stock_for_sale_sources`

Один файл-срез.

Поля:

- `project` - проект, сейчас `obvodny`
- `snapshot_month` - месяц среза
- `snapshot_date` - точная дата среза из файла
- `file_name` - имя исходного файла
- `file_hash` - hash файла для контроля импорта

### `stock_for_sale_facts`

Одна строка отчета.

Поля для маршрутизации:

- `project` - проект
- `snapshot_month` - месяц среза
- `row_type` - тип строки
- `row_label` - исходное название строки
- `property_type` - нормализованный тип объекта
- `floor_number` - этаж, если есть
- `is_in_work` - строка относится к объектам в работе

Метрики:

- `ddu_amount` - сумма ДДУ
- `dupt_markup_amount` - наценка ДУПТ
- `total_amount` - сумма ДДУ + наценка ДУПТ
- `area_sqm` - площадь
- `unit_count` - количество объектов
- `ddu_price_per_sqm` - цена за м2 по ДДУ
- `dupt_price_per_sqm` - цена за м2 по ДУПТ
- `total_price_per_sqm` - общая цена за м2

## Значения `row_type`

- `total` - строка `Всего`
- `total_with_markup` - итоговая сумма с наценкой ДУПТ из отдельной строки файла
- `category` - агрегатная категория, например `апартаменты`
- `detail` - детализация, например этаж или строка в работе

Важно: строки разных `row_type` нельзя бездумно суммировать вместе, потому что в таблице одновременно лежат итоги, категории и детализация.

## Значения `property_type`

- `total`
- `storage`
- `restaurant`
- `first_floor`
- `apartment`
- `developer_balance`
- `other`

## Будущий маппинг запросов

Примеры:

- `остатки в продаже апрель` -> последний/указанный срез, `row_type=total`
- `сколько апартаментов в продаже` -> `property_type=apartment`, обычно `row_type=category`
- `остатки по этажам` -> `row_type=detail`, `floor_number is not null`
- `1 этаж в работе` -> `floor_number=1`, `is_in_work=true`
- `цена за метр` -> `ddu_price_per_sqm`, `dupt_price_per_sqm` или `total_price_per_sqm`
