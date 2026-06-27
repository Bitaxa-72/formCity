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

## Подключенный маппинг запросов

Отчет подключен к ответам бота через `report_type=sales_report`.

Публичные метрики:

- `sales_contract_revenue` - выручка по контрактации
- `sales_contract_area_sqm` - объем контрактации, м2
- `sales_contract_count` - количество сделок / помещений
- `sales_price_per_sqm` - цена за м2
- `sales_ddu_actual_payments` - фактические оплаты по ДДУ
- `sales_ddu_remaining_payment_schedule` - график оплаты остатка по ДДУ
- `sales_cumulative_price_per_sqm` - накопительная цена за м2

Подключенные view:

- `sales_summary` - сводка по `project_total`
- `sales_by_segments` - разбивка по сегментам
- `sales_monthly` - помесячные значения продаж
- `sales_payments` - оплаты ДДУ и остаток оплат
- `sales_price_per_sqm` - цены за м2 по сегментам
- `sales_apartments` - апартаменты
- `sales_commercial_1_floor` - коммерция 1 этаж
- `sales_restaurant` - ресторан
- `sales_storage` - кладовки
- `sales_commercial_2_floor` - коммерция 2 этаж
- `sales_sh` - SH
- `sales_available_snapshots` - доступные срезы отчета
- `sales_available_periods` - доступные месяцы продаж
- `sales_available_segments` - доступные сегменты
- `sales_available_metrics` - доступные показатели
- `sales_available_owners` - доступные владельцы
- `sales_available_scenarios` - доступные сценарии

Если срез отчета не указан, backend берет последний актуальный срез.

Обычные фразы `за май`, `за март` для отчета продаж трактуются как месяц продаж внутри матрицы. Для выбора версии отчета нужно явно сказать `срез`, например `срез апрель`.

По умолчанию сводка использует `segment=project_total`, `period_kind=total`, `scenario=total`, `owner_scope=all`, чтобы не смешивать итоговые строки и сегменты.
