# Отчет о продажах

## Назначение

Отчет хранит матрицу продаж по проекту `obvodny`.

Исходные файлы:

- `Отчет о продажах (Обв.118) Stories 28.02.2026.xlsx`
- `Отчет о продажах (Обв.118) Stories 31.03.2026.xlsx`
- `Отчет о продажах (Обв.118) Stories 30.04.2026.xlsx`

## Таблицы

### `sales_report_sources`

Один файл-срез.

Поля:

- `project` - проект, сейчас `obvodny`
- `snapshot_month` - месяц среза
- `snapshot_date` - точная дата среза из файла
- `file_name` - имя исходного файла
- `file_hash` - hash файла для контроля импорта

### `sales_report_facts`

Одна строка = один показатель по одному сегменту, владельцу и периоду.

Поля маршрутизации:

- `project` - проект
- `snapshot_month` - месяц среза отчета
- `segment` - сегмент отчета
- `metric_key` - нормализованная метрика
- `owner_scope` - все / застройщик / Велл
- `period_kind` - `total` или `month`
- `period_month` - месяц значения, если это помесячная колонка
- `scenario` - `fact`, `plan` или `total`

## Сегменты

- `project_total` - итого по проекту
- `apartments` - апартаменты
- `commercial_1_floor` - коммерция 1 этаж
- `restaurant` - ресторан
- `storage` - кладовки
- `commercial_2_floor` - коммерция 2 этаж
- `sh` - SH

## Метрики

- `contract_revenue` - выручка по контрактации
- `contract_area_sqm` - объем контрактации, кв.м.
- `contract_count` - объем контрактации, шт.
- `price_per_sqm` - цена за 1 кв.м.
- `ddu_actual_payments` - фактические оплаты по ДДУ
- `ddu_remaining_payment_schedule` - график оплаты остатка по ДДУ
- `cumulative_price_per_sqm` - накопительная цена за 1 кв.м.

## Владелец

- `all` - строка общего показателя
- `developer` - застройщик
- `well` - Велл
- `well_including` - в том числе Велл

## Важные правила

Денежные показатели в исходнике указаны в `тыс.руб.` и хранятся с unit `thousand_rub`.

Колонка `Итого` хранится как `period_kind=total`, а помесячные колонки как `period_kind=month`.

При будущей логике бота нельзя смешивать `total` и `month` без явного намерения пользователя.
