## Запуск

```bash
python -m uvicorn app.main:app --reload
```

## Тесты

```bash
python -m pytest
```

Тесты не вызывают реальные Telegram/OpenAI. Внешние слои заменяются fake-объектами.

## Миграции

```bash
python -m alembic upgrade head
```

## Структура

```text
repo/
  app/ - основной код приложения
    __init__.py - делает app Python-пакетом
    access.py - проверяет доступ по username
    calculation_engine.py - выполняет SQL и считает операции по last_result
    commands.py - хранит ответы /start, /info, /clear
    config.py - читает, проверяет и безопасно описывает настройки
    context_resolver.py - применяет LLM delta к текущему dialog_state
    database.py - создает SQLAlchemy engine и DB session
    health.py - проверяет proxy для LLM, Telegram API и LLM API
    llm_answer.py - оформляет ResponseData в черновик русского ответа
    llm_dictionary.py - хранит строгий словарь intent, report_type, project, metric, group_by, operation
    llm_input.py - собирает user message, state, history и last_result для LLM
    llm_parser.py - отправляет LLM input в OpenAI и валидирует JSON-ответ
    logging_context.py - собирает безопасный JSON-контекст для логов
    main.py - запускает FastAPI и принимает Telegram webhook
    metric_catalog.py - хранит доступные метрики по типам отчетов
    metric_resolver.py - проверяет метрики, группировки, фильтры и проекты query frame
    models.py - описывает таблицы users, dialog_states, message_history, last_results
    query_frame.py - собирает нормализованный query frame и проверяет готовность запроса
    repositories.py - загружает user session, сохраняет state, history и last_result
    response_data.py - готовит чистый JSON для будущего ответа пользователю
    result_verifier.py - проверяет расчетный результат перед подготовкой ответа
    sql_compiler.py - собирает безопасный SQL из QueryFrame и MetricResolution
    telegram_client.py - отправляет сообщения через Telegram API
    telegram_response.py - разбивает и отправляет финальный ответ в Telegram
    telegram_schemas.py - описывает Telegram update через Pydantic
  migrations/ - Alembic-миграции БД
    versions/ - версии миграций
      20260622_0001_user_session.py - создает таблицы user session
    env.py - Alembic env, берет DATABASE_URL из config
  tests/ - тесты проекта
    test_calculation_engine.py - проверяет выполнение SQL, округление и операции
    test_config.py - проверяет чтение и валидацию настроек
    test_context_resolver.py - проверяет обновление контекста после LLM parsing
    test_llm_answer.py - проверяет schema черновика ответа и fallback
    test_llm_input.py - проверяет сбор входа для LLM
    test_llm_parser.py - проверяет строгую schema JSON-ответа LLM
    test_logging_context.py - проверяет безопасный контекст логов
    test_metric_resolver.py - проверяет предметную валидацию метрик
    test_query_frame.py - проверяет готовность query frame и уточняющие вопросы
    test_quest_scenarios.py - проверяет сценарии из quest.md через pipeline
    test_response_data.py - проверяет подготовку JSON для ответа
    test_result_verifier.py - проверяет валидацию расчетного результата
    test_sql_compiler.py - проверяет сборку SQL и отказы компилятора
    test_telegram_response.py - проверяет разбиение и отправку Telegram ответа
    test_user_session_repository.py - проверяет users, state, history, last_result и сохранение ответа
    test_webhook.py - проверяет webhook, whitelist, команды и health checks
  .env - хранит локальные секреты и настройки
  .gitignore - исключает секреты, cache и локальные DB-файлы из git
  alembic.ini - конфиг Alembic
  README.md - описание структуры проекта
  requirements.txt - список Python-зависимостей, включая OpenAI SDK
```


## Текущее дерево контекста

```json
{
  "report_type": null,
  "project": null,
  "period": {
    "from": null,
    "to": null,
    "label": null
  },
  "metrics": [],
  "filters": {},
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": null,
  "awaiting_clarification": false,
  "clarification_target": null
}
```

## Словарь для ии

### `intent`

```text
data_query - новый запрос к данным
context_query - уточнение прошлого запроса
math_on_last_result - расчет по последнему результату
clarification_answer - ответ на уточняющий вопрос бота
general_question - общий вопрос без расчета данных
unsupported - неподдерживаемый запрос
```

### `report_type`

```text
summary - сводный отчет
model - модель
payment_calendar - платежный календарь
roadmap - дорожная карта
sales_report - отчет о продажах
sales_plan_execution - отчет об исполнении плана продаж
agents_report - отчет по агентам
stock_for_sale - остатки в продаже
debt_and_bookings - ДЗ и брони
non_project_expenses - непроектные расходы
unknown - тип отчета не определен
```

### `project`

```text
obvodny_118 - Обводный 118
well_moskovsky - Велл Московский
evgenievsky - Евгеньевский
all - все проекты
unknown - проект не определен
```

### `metric`

```text
revenue - выручка
sold_area - проданная площадь
deal_count - количество сделок
average_deal_price - средняя цена сделки
price_per_square_meter - цена за квадратный метр
debt - задолженность
booking_amount - сумма брони
plan - план
fact - факт
deviation - отклонение
agent_commission - агентское вознаграждение
pledge_release_amount - сумма вывода из залога
remaining_amount - остаток
unknown - метрика не определена
```

### `group_by`

```text
project - по проектам
period - по периоду
month - по месяцам
quarter - по кварталам
year - по годам
floor - по этажам
room_type - по типам помещений
agent - по агентам
bank - по банкам
metric - по метрикам
```

### `operation.type`

```text
add - сложить
subtract - вычесть
multiply - умножить
divide - разделить
percent - посчитать процент
difference - посчитать разницу
ratio - посчитать отношение
average - посчитать среднее
compare_periods - сравнить периоды
same_metric_other_period - та же метрика за другой период
```

### `operation.source`

```text
last_result - последний результат
dialog_state - текущий контекст
literal - число или строка из запроса
```

## JSON-формат ответа ии

ии возвращает только JSON.

```json
{
  "intent": "data_query",
  "state_delta": {
    "report_type": "sales_report",
    "project": "obvodny_118",
    "period": {
      "from": "2026-03-01",
      "to": "2026-03-31",
      "label": "март 2026"
    },
    "metrics": ["revenue"],
    "filters": {},
    "group_by": []
  },
  "operation": null,
  "needs_clarification": false,
  "clarification_question": null,
  "confidence": 0.95
}
```

Пример расчета по последнему результату:

```json
{
  "intent": "math_on_last_result",
  "state_delta": {},
  "operation": {
    "type": "divide",
    "left": {
      "source": "last_result",
      "metric": "revenue"
    },
    "right": {
      "source": "literal",
      "value": 2
    }
  },
  "needs_clarification": false,
  "clarification_question": null,
  "confidence": 0.9
}
```

Если данных не хватает:

```json
{
  "intent": "data_query",
  "state_delta": {
    "metrics": ["revenue"]
  },
  "operation": null,
  "needs_clarification": true,
  "clarification_question": "Уточните проект или период для расчета выручки.",
  "confidence": 0.7
}
```

## QueryFrame

`QueryFrame` собирается после Context Resolver.

Он не строит SQL и не считает данные. Его задача - понять, готов ли запрос к предметной проверке и дальнейшей компиляции.

### Defaults

```text
report_type = summary
project = all
period.label = весь доступный период
```

### JSON-формат QueryFrame

```json
{
  "intent": "data_query",
  "report_type": "sales_report",
  "project": "obvodny_118",
  "period": {
    "from": "2026-03-01",
    "to": "2026-03-31",
    "label": "март 2026"
  },
  "metrics": ["revenue"],
  "filters": {},
  "group_by": ["floor"],
  "operation": null,
  "ready": true,
  "missing_fields": [],
  "clarification_question": null
}
```

Если данных не хватает:

```json
{
  "intent": "data_query",
  "report_type": "summary",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "весь доступный период"
  },
  "metrics": [],
  "filters": {},
  "group_by": [],
  "operation": null,
  "ready": false,
  "missing_fields": ["metrics"],
  "clarification_question": "Уточните метрику для запроса."
}
```

Для математики:

```json
{
  "intent": "math_on_last_result",
  "report_type": "summary",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "весь доступный период"
  },
  "metrics": [],
  "filters": {},
  "group_by": [],
  "operation": {
    "type": "divide",
    "left": {
      "source": "last_result",
      "metric": "revenue"
    },
    "right": {
      "source": "literal",
      "value": 2
    }
  },
  "ready": true,
  "missing_fields": [],
  "clarification_question": null
}
```

## MetricCatalog

`MetricCatalog` хранит предметные правила: какие метрики доступны в каком типе отчета.

Формат одной метрики:

```json
{
  "unit": "rub",
  "group_by": ["project", "period", "month"],
  "filters": ["project", "period"],
  "projects": ["all", "obvodny_118"],
  "privacy": "safe_aggregate"
}
```

### Текущий каталог

```text
summary
  revenue
  sold_area
  deal_count

sales_report
  revenue
  sold_area
  deal_count
  average_deal_price
  price_per_square_meter

payment_calendar
  plan
  fact
  deviation
  remaining_amount

agents_report
  deal_count
  agent_commission

debt_and_bookings
  debt
  booking_amount

roadmap
  pledge_release_amount
```

## MetricResolution

`MetricResolution` собирается после `QueryFrame`.

Он проверяет:

```text
существует ли report_type
доступна ли metric для report_type
доступен ли project для metric
доступен ли group_by для metric
доступен ли filter для metric
```

### JSON-формат MetricResolution

```json
{
  "valid": true,
  "metrics": [
    {
      "name": "revenue",
      "unit": "rub",
      "privacy": "safe_aggregate"
    }
  ],
  "errors": [],
  "clarification_question": null
}
```

Если метрика не подходит:

```json
{
  "valid": false,
  "metrics": [],
  "errors": ["metric_not_allowed_for_report_type"],
  "clarification_question": "Уточните метрику или тип отчета."
}
```

### Ошибки MetricResolver

```text
query_frame_not_ready - QueryFrame еще не готов
unknown_report_type - неизвестный тип отчета
metric_not_allowed_for_report_type - метрика недоступна для типа отчета
group_by_not_allowed_for_metric - группировка недоступна для метрики
filter_not_allowed_for_metric - фильтр недоступен для метрики
project_not_allowed_for_metric - проект недоступен для метрики
```

## SQLCompiler

`SQLCompiler` собирается после `MetricResolution`.

Он не выполняет SQL и не считает результат. Его задача - превратить проверенный `QueryFrame` в параметризованный SQL.

LLM не пишет SQL напрямую. Таблицы, колонки, выражения метрик, группировки и фильтры берутся только из белых списков внутри `sql_compiler.py`.

### Правила

```text
QueryFrame должен быть ready=true
MetricResolution должен быть valid=true
operation не компилируется в SQL
metrics не должны быть пустыми
таблица выбирается по report_type
колонки выбираются по metric, group_by и filters
значения идут только через params
```

### JSON-формат SQLQuery

```json
{
  "sql": "SELECT\n  floor AS floor,\n  SUM(revenue_amount) AS revenue\nFROM sales_facts\nWHERE project = :project\nGROUP BY floor",
  "params": {
    "project": "obvodny_118"
  },
  "table": "sales_facts",
  "metrics": ["revenue"],
  "group_by": ["floor"]
}
```

### Текущие SQL-шаблоны

```text
summary -> summary_facts
sales_report -> sales_facts
payment_calendar -> payment_calendar_facts
agents_report -> agent_facts
debt_and_bookings -> debt_booking_facts
roadmap -> roadmap_facts
```

Названия таблиц и колонок сейчас являются каркасом. После разбора реальных Excel-таблиц и финальной схемы БД этот слой обновляется в одном месте - `sql_compiler.py`.

### Ошибки SQLCompiler

```text
query_frame_not_ready - QueryFrame еще не готов
metric_resolution_not_valid - метрики не прошли проверку
operation_query_not_supported - это расчет по последнему результату, не SQL-запрос
empty_metrics - нет метрик для SELECT
unknown_report_type - нет SQL-шаблона для типа отчета
unknown_metric - нет SQL-выражения для метрики
unknown_group_by - нет SQL-колонки для группировки
unknown_filter - нет SQL-колонки для фильтра
empty_filter_value - фильтр передан пустым списком
```

## CalculationEngine

`CalculationEngine` работает после `SQLCompiler`.

Он выполняет параметризованный SQL через SQLAlchemy или считает операцию по `last_result`.

Он не формирует текст ответа пользователю. Его задача - вернуть структурированный результат для следующих этапов.

### Правила

```text
SQL берется только из SQLQuery
params передаются отдельно
raw SQL от LLM не принимается
строки приводятся к обычному JSON
Decimal и float округляются до 2 знаков
даты переводятся в ISO-строки
деление на ноль запрещено
```

### JSON-формат CalculationResult

```json
{
  "kind": "sql_result",
  "rows": [
    {
      "project": "obvodny_118",
      "revenue": 150.26,
      "deal_count": 2
    }
  ],
  "row_count": 1,
  "metrics": ["revenue", "deal_count"],
  "columns": ["project", "revenue", "deal_count"],
  "operation": null
}
```

Для операции по последнему результату:

```json
{
  "kind": "operation_result",
  "rows": [
    {
      "value": 50.78
    }
  ],
  "row_count": 1,
  "metrics": ["value"],
  "columns": ["value"],
  "operation": {
    "type": "divide",
    "left": {
      "source": "last_result",
      "metric": "revenue"
    },
    "right": {
      "source": "literal",
      "value": 2
    }
  }
}
```

### Ошибки CalculationEngine

```text
sql_execution_failed - SQL не выполнился
sql_query_missing - нет SQLQuery
last_result_missing - нет прошлого результата
metric_value_not_found - метрика не найдена в last_result
operation_operand_missing - нет операнда операции
literal_value_not_numeric - literal не является числом
metric_name_missing - не указана метрика
operation_source_not_supported - источник операнда не поддержан
operation_type_not_supported - тип операции не поддержан
division_by_zero - деление на ноль
```

## ResultVerifier

`ResultVerifier` работает после `CalculationEngine`.

Он не выполняет SQL, не считает значения и не пишет ответ пользователю. Его задача - проверить, что расчетный результат можно безопасно передавать дальше.

### Правила

```text
результат должен существовать
результат не должен быть пустым
ожидаемые метрики должны быть в columns или metrics
если в rows есть project, он должен совпадать с QueryFrame.project
если в rows есть дата, она должна попадать в QueryFrame.period
source фиксирует отчет, проект, период, метрики и единицы
```

### JSON-формат ResultVerification

```json
{
  "verified": true,
  "errors": [],
  "warnings": [],
  "row_count": 1,
  "metrics": ["revenue"],
  "columns": ["project", "revenue"],
  "source": {
    "report_type": "sales_report",
    "project": "obvodny_118",
    "period": {
      "from": null,
      "to": null,
      "label": "весь доступный период"
    },
    "metrics": ["revenue"],
    "units": {
      "revenue": "rub"
    },
    "kind": "sql_result"
  }
}
```

### Ошибки ResultVerifier

```text
result_missing - CalculationResult отсутствует
empty_result - расчет вернул 0 строк
metric_column_missing - ожидаемой метрики нет в результате
project_mismatch - проект в результате не совпадает с запросом
period_out_of_range - дата в результате вне запрошенного периода
```

### Предупреждения ResultVerifier

```text
columns_empty - список колонок пустой
```

## ResponseData

`ResponseData` работает после `ResultVerifier`.

Он не пишет финальный текст пользователю. Его задача - собрать чистый JSON, который можно передать в следующий слой `LLM answer`.

### Правила

```text
готовится только проверенный результат
применяется политика приватности колонок
чувствительные ячейки не передаются в LLM answer
summary берет значения из первой строки
table ограничивается первыми 10 строками
raw rows не передаются без обрезки
метрики получают русские подписи
единицы получают короткие подписи
source переносится из ResultVerification
errors и warnings сохраняются
```

### Политика колонок

Точная политика будет заполнена после финальной схемы БД и разбора реальных таблиц.

Идея:

```text
allowed - можно передавать в LLM answer
hidden - полностью убрать из ResponseData
masked - заменить на безопасное значение
aggregate_only - можно использовать в расчетах, но нельзя отдавать отдельными строками
```

Пример будущего словаря:

```json
{
  "project": "allowed",
  "revenue": "allowed",
  "agent_name": "masked",
  "client_name": "hidden",
  "phone": "hidden",
  "email": "hidden",
  "passport": "hidden",
  "contract_number": "masked"
}
```

### JSON-формат ResponseData

```json
{
  "ready": true,
  "title": "Выручка: sales_report, obvodny_118",
  "summary": [
    {
      "metric": "revenue",
      "label": "Выручка",
      "value": 150.26,
      "unit": "руб."
    }
  ],
  "table": {
    "columns": ["project", "revenue"],
    "rows": [
      {
        "project": "obvodny_118",
        "revenue": 150.26
      }
    ],
    "total_rows": 1,
    "truncated": false
  },
  "source": {
    "report_type": "sales_report",
    "project": "obvodny_118",
    "period": {
      "from": null,
      "to": null,
      "label": "весь доступный период"
    },
    "metrics": ["revenue"],
    "units": {
      "revenue": "rub"
    },
    "kind": "sql_result"
  },
  "warnings": [],
  "errors": []
}
```

Если результат не готов:

```json
{
  "ready": false,
  "title": "Результат отсутствует",
  "summary": [],
  "table": null,
  "source": {},
  "warnings": [],
  "errors": ["result_missing"]
}
```

## LLMAnswer

`LLMAnswer` работает после `ResponseData`.

Он оформляет проверенные данные в черновик русского ответа. Новые цифры, новые расчеты и SQL запрещены системным prompt.

### Правила

```text
на вход идет только ResponseData
если ResponseData.ready=false, возвращается fallback без вызова LLM
LLM возвращает только JSON
черновик проходит Pydantic validation
LLM не должна добавлять новые числа
LLM не должна упоминать SQL, JSON и backend
```

### JSON-формат AnswerDraft

```json
{
  "text": "Выручка по проекту Обводный 118 составила 150.26 руб.",
  "used_metrics": ["revenue"],
  "source": {
    "report_type": "sales_report",
    "project": "obvodny_118"
  },
  "warnings": []
}
```

Если данные не готовы:

```json
{
  "text": "Не удалось подготовить проверенный ответ по данным.",
  "used_metrics": [],
  "source": {},
  "warnings": ["result_missing"]
}
```

### Ошибки LLMAnswer

```text
OPENAI_KEY is not configured - нет ключа OpenAI
OPENAI_MODEL is not configured - нет модели OpenAI
LLM returned empty answer - LLM вернула пустой ответ
LLM returned invalid answer JSON - LLM вернула не JSON
LLM returned invalid answer schema - LLM вернула JSON не по schema
```

## TelegramResponse

`TelegramResponse` работает после `LLMAnswer`.

Он берет `AnswerDraft.text`, разбивает длинный текст на части и отправляет их в Telegram.

### Правила

```text
пустой текст заменяется fallback
длинный текст режется на chunks
chunk меньше лимита Telegram
части отправляются по порядку
ошибка отправки не ломает webhook
статус отправки пишется отдельно
```

### JSON-формат TelegramResponseStatus

```json
{
  "sent": true,
  "chunks": 1,
  "error": null
}
```

Если отправка не прошла:

```json
{
  "sent": false,
  "chunks": 0,
  "error": "RuntimeError"
}
```

## SaveState

`SaveState` работает после `TelegramResponse`.

Он сохраняет итог обработки запроса в уже существующие таблицы.

### Что сохраняется

```text
dialog_states.data - текущий state и last_trace
last_results.data - последний проверенный CalculationResult
last_results.query_frame - QueryFrame последнего результата
message_history - сообщение assistant, если ответ отправлен
```

### Правила

```text
state сохраняется после успешного LLM parsing
last_result сохраняется только если ResultVerifier.verified=true
assistant message сохраняется только если TelegramResponse.sent=true
last_trace хранит технические статусы без секретов
новая миграция не нужна, используются текущие таблицы
```

### Пример last_trace

```json
{
  "request_id": "uuid",
  "intent": "data_query",
  "query_ready": true,
  "metrics_valid": true,
  "sql_compiled": true,
  "calculation_done": true,
  "result_verified": true,
  "response_data_ready": true,
  "llm_answer_done": true,
  "telegram_response_sent": true
}
```

## Logs

`Logs` собирают безопасный технический контекст обработки запроса.

Финальный лог пишется как `request_completed` с JSON-контекстом.

### Что логируется

```text
request_id
username
update_id
chat_id
intent
query_frame summary
statuses
errors
```

### Правила

```text
секреты не логируются
значения filters не логируются
логируются только имена filters
token/key/secret/password/proxy маскируются
phone/email/passport маскируются
сырые ответы LLM не логируются
сырые строки результата не логируются
```

### JSON-формат request_completed

```json
{
  "request_id": "uuid",
  "username": "tester",
  "update_id": 1001,
  "chat_id": 777,
  "intent": "data_query",
  "query_frame": {
    "intent": "data_query",
    "report_type": "sales_report",
    "project": "obvodny_118",
    "period": {
      "from": null,
      "to": null,
      "label": "весь доступный период"
    },
    "metrics": ["revenue"],
    "filter_names": ["room_type"],
    "group_by": [],
    "ready": true,
    "missing_fields": [],
    "has_operation": false
  },
  "statuses": {
    "query_ready": true,
    "metrics_valid": true,
    "telegram_response_sent": true,
    "state_saved": true
  },
  "errors": {
    "metric_errors": [],
    "sql_error": null,
    "calculation_error": null
  }
}
```
