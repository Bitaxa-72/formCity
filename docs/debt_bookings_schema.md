# ДЗ и брони

Отчет `debt_and_bookings` подключен к backend-ответам Telegram через безопасный агрегированный слой.

## Источник

Папка: `оригиналы таблиц/дз и брони`

Файлы:
- `Отчет о ДЗ и Бронях.xlsx`
- `Отчет о ДЗ и Бронях_апрель 2026.xlsx`
- `Отчет о ДЗ и Бронях_март 2026.xlsx`

Проект по умолчанию: `obvodny`.

## Таблицы

### `debt_booking_sources`

Файлы-источники и даты срезов.

Ключевые поля:
- `project`
- `snapshot_month`
- `snapshot_date`
- `file_name`
- `file_hash`

### `debt_booking_items`

Основной лист отчета. Здесь лежат строки ДЗ и броней.

Ключевые поля:
- `project`
- `snapshot_month`
- `snapshot_date`
- `row_type` - `category` или `detail`
- `item_kind` - тип строки
- `section` - раздел, внутри которого лежит строка
- `client_name`
- `manager_name`
- `is_special_client`
- `unit_number`
- `total_amount`
- `comments`
- `contacts`

Типы `item_kind`:
- `total` - итоговая строка
- `registered` - зарегистрировано
- `overdue` - просроченные
- `current` - текущие
- `dupt_signed_unregistered` - ДУПТ подписан, не зарегистрирован
- `booking` - брони
- `detail` - детальная строка без распознанного раздела

### `debt_booking_monthly_values`

Помесячные значения из основного листа.

Ключевые поля:
- `project`
- `snapshot_month`
- `snapshot_date`
- `item_source_row`
- `item_kind`
- `row_type`
- `period_month`
- `value`

### `debt_booking_deviations`

Лист `Отклонения`.

Ключевые поля:
- `project`
- `snapshot_month`
- `snapshot_date`
- `period_month`
- `row_type`
- `item_kind`
- `section`
- `client_name`
- `unit_number`
- `plan_amount`
- `updated_plan_amount`
- `fact_payment_amount`
- `remaining_amount`
- `plan_comment`
- `fact_comment`

### `debt_booking_refusals`

Лист `Отказы`.

Ключевые поля:
- `project`
- `snapshot_month`
- `snapshot_date`
- `customer_name`
- `status`
- `area_sqm`
- `unit_number`
- `full_price_amount`
- `payment_type`
- `reason`
- `agency`
- `manager_name`

## Безопасность

В отчете есть персональные данные, контакты, комментарии и причины отказов.

Все строки импортируются с:
- `is_sensitive = true`
- заполненным `sensitive_fields`

Эти поля можно использовать для фильтрации и расчетов, но нельзя напрямую выводить пользователю в ответах Telegram:
- ФИО клиентов и покупателей
- контакты
- менеджеры
- комментарии
- причины отказов

Номера помещений разрешены к выводу без ФИО, контактов, комментариев и других персональных полей.

Для будущей backend-логики безопасный формат ответа должен агрегировать данные: суммы, количество строк, распределения по статусам, периодам, разделам и номерам помещений.

## Подключенные ответы

Backend выводит только агрегаты:

- количество строк;
- сумма ДЗ и броней;
- помесячные суммы;
- отклонения: план, уточненный план, факт оплат, остаток;
- отказы: количество, площадь, сумма;
- списки доступных срезов, типов строк, разделов, номеров помещений, статусов и способов оплаты.

Поддерживаемые view:

```text
debt_bookings_summary
debt_bookings_monthly
debt_bookings_deviations
debt_bookings_refusals
debt_bookings_bookings
debt_bookings_overdue
debt_bookings_current
debt_bookings_registered
debt_bookings_available_periods
debt_bookings_available_kinds
debt_bookings_available_sections
debt_bookings_available_unit_numbers
debt_bookings_available_statuses
debt_bookings_available_payment_types
```
