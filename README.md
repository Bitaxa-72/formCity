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
  docs/ - проектная документация
    agents_report_schema.md - схема БД для отчета по агентам
    architecture_scheme.css - стили для полной HTML-схемы проекта
    architecture_scheme.html - полная визуальная схема архитектуры и развилок
    context_flow.md - схема жизни контекста и правила переходов
    debt_bookings_schema.md - схема БД для ДЗ и броней
    non_project_expenses_schema.md - схема БД для непроектных расходов
    sales_plan_execution_schema.md - схема БД для исполнения плана продаж
    sales_report_schema.md - схема БД для отчета о продажах
    stock_for_sale_schema.md - схема БД для остатков в продаже
    summary_schema.md - схема БД для сводного отчета
  app/ - основной код приложения
    __init__.py - делает app Python-пакетом
    main.py - запускает FastAPI и обрабатывает Telegram update
    health.py - проверяет proxy для LLM, Telegram API и LLM API
    bot/ - Telegram-слой
      __init__.py - делает bot Python-пакетом
      commands.py - хранит ответы /start, /info, /clear, /admin
      polling.py - запускает Telegram long polling для сервера без HTTPS webhook
      telegram_client.py - работает с Telegram API: сообщения, PDF, webhook, updates
      telegram_response.py - разбивает и отправляет финальный ответ в Telegram
      telegram_schemas.py - описывает Telegram update через Pydantic
    core/ - базовые настройки и доступ
      __init__.py - делает core Python-пакетом
      access.py - проверяет доступ по username
      config.py - читает, проверяет и безопасно описывает настройки
    db/ - работа с базой данных
      __init__.py - делает db Python-пакетом
      database.py - создает SQLAlchemy engine и DB session
      models.py - описывает таблицы приложения и отчетов
      repositories.py - загружает user session, сохраняет state, history и last_result
    importers/ - импорт данных из исходных таблиц в БД
      __init__.py - делает importers Python-пакетом
      agents_report.py - загружает отчет по агентам из xlsx
      debt_bookings.py - загружает ДЗ и брони из xlsx
      model.py - загружает модель из xlsx
      non_project_expenses.py - загружает непроектные расходы из xlsx
      payment_calendar.py - загружает платежный календарь из xlsx
      roadmap.py - загружает дорожную карту из xlsx
      sales_plan_execution.py - загружает исполнение плана продаж из xlsx
      sales_report.py - загружает отчет о продажах из xlsx
      stock_for_sale.py - загружает остатки в продаже из xlsx
      summary.py - загружает сводные таблицы из xlsx
    llm/ - слой работы с LLM
      __init__.py - делает llm Python-пакетом
      answer.py - оформляет ResponseData в черновик русского ответа
      dictionary.py - хранит строгий словарь intent, report_type, project, metric, dimension, group_by, operation
      input.py - собирает user message, state, history и last_result для LLM
      parser.py - отправляет LLM input в OpenAI, валидирует JSON-ответ и делает один repair-pass при schema error
    pipeline/ - контекст, SQL, расчеты и подготовка результата
      __init__.py - делает pipeline Python-пакетом
      calculation_engine.py - выполняет SQL и считает операции по last_result
      context_resolver.py - применяет LLM delta к текущему dialog_state
      logging_context.py - собирает безопасный JSON-контекст для логов
      domain_resolver.py - сверяет свободные значения фильтров с реальными значениями БД
      metric_catalog.py - хранит доступные метрики по типам отчетов
      metric_resolver.py - проверяет метрики, группировки, фильтры и проекты query frame
      pdf_report.py - формирует PDF для больших табличных отчетов
      query_frame.py - собирает нормализованный query frame и проверяет готовность запроса
      response_data.py - готовит чистый JSON для будущего ответа пользователю
      result_verifier.py - проверяет расчетный результат перед подготовкой ответа
      sql_compiler.py - собирает безопасный SQL из QueryFrame и MetricResolution
  migrations/ - Alembic-миграции БД
    versions/ - версии миграций
      20260622_0001_user_session.py - создает таблицы user session
      20260622_0002_payment_calendar_facts.py - создает таблицу платежного календаря
      20260625_0005_non_project_expenses.py - создает таблицы непроектных расходов
      20260625_0006_stock_for_sale.py - создает таблицы остатков в продаже
      20260625_0007_sales_report.py - создает таблицы отчета о продажах
      20260625_0008_sales_plan_execution.py - создает таблицы исполнения плана продаж
      20260626_0009_agents_report.py - создает таблицы отчета по агентам
      20260626_0010_debt_bookings.py - создает таблицы ДЗ и броней
      20260626_0011_summary_tables.py - создает таблицы сводного отчета
    env.py - Alembic env, берет DATABASE_URL из config
  tests/ - тесты проекта
    test_agents_report_importer.py - проверяет импорт отчета по агентам
    test_calculation_engine.py - проверяет выполнение SQL, округление и операции
    test_config.py - проверяет чтение и валидацию настроек
    test_context_resolver.py - проверяет обновление контекста после LLM parsing
    test_debt_bookings_importer.py - проверяет импорт ДЗ и броней
    test_domain_resolver.py - проверяет поиск и уточнение свободных фильтров по данным БД
    test_llm_answer.py - проверяет schema черновика ответа и fallback
    test_llm_input.py - проверяет сбор входа для LLM
    test_llm_parser.py - проверяет строгую schema JSON-ответа LLM
    test_logging_context.py - проверяет безопасный контекст логов
    test_metric_resolver.py - проверяет предметную валидацию метрик
    test_model_importer.py - проверяет импорт модели
    test_model_report.py - проверяет ответы по модели
    test_model_tables.py - проверяет таблицы модели
    test_non_project_expenses_importer.py - проверяет импорт непроектных расходов
    test_non_project_expenses_report.py - проверяет ответы по непроектным расходам
    test_payment_calendar_importer.py - проверяет импорт платежного календаря
    test_pdf_report.py - проверяет формирование PDF
    test_query_frame.py - проверяет готовность query frame и уточняющие вопросы
    test_quest_scenarios.py - проверяет сценарии из quest.md через pipeline
    test_response_data.py - проверяет подготовку JSON для ответа
    test_result_verifier.py - проверяет валидацию расчетного результата
    test_roadmap_corrections.py - проверяет корректировки дорожной карты
    test_roadmap_importer.py - проверяет импорт дорожной карты
    test_roadmap_report.py - проверяет ответы по дорожной карте
    test_sales_plan_execution_importer.py - проверяет импорт исполнения плана продаж
    test_sales_report_importer.py - проверяет импорт отчета о продажах
    test_sensitive_data.py - проверяет защиту чувствительных данных
    test_sql_compiler.py - проверяет сборку SQL и отказы компилятора
    test_stock_for_sale_importer.py - проверяет импорт остатков в продаже
    test_summary_importer.py - проверяет импорт сводных таблиц
    test_telegram_response.py - проверяет разбиение и отправку Telegram ответа
    test_user_session_repository.py - проверяет users, state, history, last_result и сохранение ответа
    test_webhook.py - проверяет webhook, whitelist, команды и health checks
  .env - хранит локальные секреты и настройки
  .dockerignore - исключает секреты, cache и локальные DB-файлы из Docker build
  .gitignore - исключает секреты, cache и локальные DB-файлы из git
  alembic.ini - конфиг Alembic
  compose.yaml - запускает web и bot сервисы в Docker Compose
  Dockerfile - собирает Python-образ приложения
  formcity.db - локальная SQLite БД для первых тестовых данных
  README.md - описание структуры проекта
  requirements.txt - список Python-зависимостей, включая OpenAI SDK
```

## Env

```text
BOT_TOKEN - Telegram bot token
OPENAI_KEY - ключ OpenAI
OPENAI_MODEL - модель OpenAI
PROXY - proxy только для LLM
TELEGRAM_PROXY - proxy для Telegram API, если сервер не открывает api.telegram.org напрямую
DATABASE_URL - строка подключения к БД
ALLOWED_USERNAMES - пользователи с доступом к боту
ADMIN_USERNAMES - пользователи с доступом к /admin
```

## Admin Debug

`/admin` доступен только пользователям из `ADMIN_USERNAMES`.

Команда работает как переключатель:

```text
/admin - включить admin debug
/admin - выключить admin debug
```

Когда режим включен, бот отправляет администратору отдельные JSON-сообщения по этапам:

```text
01 LLMInput
02 LLMParsedResponse
03 DialogState
04 QueryFrame
05 DomainResolution
06 MetricResolution
07 SQLQuery
08 CalculationResult
09 ResultVerification
10 ResponseData
11 AnswerDraft или PDFReport
12 TelegramResponseStatus
```

Длинные debug-сообщения режутся на несколько сообщений по лимиту Telegram.


## Команды

```text
/start - отправляет приветствие и сбрасывает рабочий контекст
/info - показывает справку
/clear - сбрасывает рабочий контекст
/admin - включает или выключает admin debug
```

`/start` и `/clear` не выключают `admin_debug_enabled`.


## Цепочка работы бота

Порядок чтения документации и порядок выполнения запроса:

```text
1. TelegramUpdate
   файл: app/bot/telegram_schemas.py
   смысл: принять update, достать message, chat, user, text

2. Access
   файл: app/core/access.py
   смысл: проверить username по allowlist

3. UserSession
   файлы: app/db/repositories.py, app/db/models.py
   смысл: загрузить или создать пользователя, state, history, last_result

4. CommandRouter
   файл: app/bot/commands.py
   смысл: обработать /start, /info, /clear, /admin без LLM

5. HealthCheck
   файл: app/health.py
   смысл: проверить Telegram, LLM API и proxy для LLM

6. LLMInput
   файл: app/llm/input.py
   смысл: собрать user message, dialog_state, history, last_result_summary

7. LLMDictionary
   файл: app/llm/dictionary.py
   смысл: строгие значения intent, report_type, project, metric, dimension, group_by, operation

8. LLMParsedResponse
   файл: app/llm/parser.py
   смысл: получить от LLM строгий JSON с intent, state_delta, operation

9. ContextResolver
   файл: app/pipeline/context_resolver.py
   смысл: применить state_delta к текущему dialog_state

10. QueryFrame
    файл: app/pipeline/query_frame.py
    смысл: собрать нормальную структуру запроса и понять, готов ли запрос

11. MetricCatalog
    файл: app/pipeline/metric_catalog.py
    смысл: предметные правила доступных метрик, фильтров, группировок и проектов

12. DomainResolver
    файл: app/pipeline/domain_resolver.py
    смысл: нормализовать свободные значения фильтров, например article, по реальным данным БД

13. MetricResolution
    файл: app/pipeline/metric_resolver.py
    смысл: проверить QueryFrame по MetricCatalog

14. SQLCompiler
    файл: app/pipeline/sql_compiler.py
    смысл: собрать безопасный SQL только из whitelist

15. CalculationEngine
    файл: app/pipeline/calculation_engine.py
    смысл: выполнить SQL или посчитать операцию по last_result

16. ResultVerifier
    файл: app/pipeline/result_verifier.py
    смысл: проверить, что результат можно отдавать дальше

17. ResponseData
    файл: app/pipeline/response_data.py
    смысл: собрать чистый JSON для ответа, без лишних и чувствительных данных

18. PDFReport
    файл: app/pipeline/pdf_report.py
    смысл: большие табличные отчеты оформить в PDF без LLM

19. LLMAnswer
    файл: app/llm/answer.py
    смысл: превратить ResponseData в русский текст ответа

20. TelegramResponse
    файл: app/bot/telegram_response.py
    смысл: разбить длинный текст и отправить в Telegram

21. SaveState
    файл: app/db/repositories.py
    смысл: сохранить dialog_state, last_result, assistant message

22. Logs
    файл: app/pipeline/logging_context.py
    смысл: записать безопасный технический лог без секретов и сырых данных
```

Главная цепочка JSON:

```text
TelegramUpdate
-> LLMInput
-> LLMParsedResponse
-> DialogState
-> QueryFrame
-> DomainResolution
-> MetricResolution
-> SQLQuery
-> CalculationResult
-> ResultVerification
-> ResponseData
-> PDFReport или AnswerDraft
-> TelegramResponseStatus
```

Что проходит по цепочке:

```text
TelegramUpdate - сырой update от Telegram
LLMInput - данные для LLM: текст, state, history, last_result
LLMParsedResponse - строгий JSON от LLM
DialogState - сохраненный контекст пользователя
QueryFrame - нормализованный запрос к данным
DomainResolution - сверка свободных фильтров с реальными значениями БД
MetricResolution - результат проверки метрик и правил
SQLQuery - безопасный SQL и params
CalculationResult - результат SQL или операции
ResultVerification - проверка расчетного результата
ResponseData - чистый JSON для подготовки ответа
PDFReport - PDF-документ для большого табличного отчета
AnswerDraft - черновик текста ответа
TelegramResponseStatus - статус отправки в Telegram
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
  "dimension": null,
  "filters": {},
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": null,
  "awaiting_clarification": false,
  "clarification_target": null
}
```

## Карта дерева отчетов

Это общая карта предметной области для вычисления полного дерева запросов. Верхний уровень - `report_type`, внутри идут доступные проекты, метрики, измерения, группировки и фильтры.

Порядок уровней:

```text
report_type
-> project
-> request_kind
   -> metrics
   -> dimensions
-> filters
-> group_by
```

```json
{
  "summary": {
    "status": "planned",
    "projects": ["all", "obvodny", "moskovsky", "evgenievsky"],
    "metrics": [],
    "dimensions": [],
    "group_by": [],
    "filters": {}
  },
  "model": {
    "status": "planned",
    "projects": ["all", "obvodny", "moskovsky", "evgenievsky"],
    "metrics": [],
    "dimensions": [],
    "group_by": [],
    "filters": {}
  },
  "payment_calendar": {
    "status": "active",
    "table": "payment_calendar_facts",
    "projects": {
      "all": {
        "label": "все проекты"
      },
      "obvodny": {
        "label": "Обводный"
      },
      "moskovsky": {
        "label": "Московский"
      }
    },
    "metrics": {
      "plan": {
        "label": "план",
        "column": "plan_amount",
        "unit": "rub"
      },
      "fact": {
        "label": "факт",
        "column": "fact_amount",
        "unit": "rub"
      },
      "deviation": {
        "label": "отклонение",
        "column": "deviation_amount",
        "unit": "rub"
      }
    },
    "dimensions": {
      "article": {
        "label": "статья",
        "column": "article"
      },
      "article_kind": {
        "label": "тип строки",
        "column": "article_kind",
        "values": ["payment_total", "income_total", "balance_start", "balance_end", "detail"]
      },
      "period_month": {
        "label": "месяц",
        "column": "period_month"
      },
      "project": {
        "label": "проект",
        "column": "project"
      }
    },
    "group_by": ["project", "month", "article", "article_kind"],
    "filters": {
      "project": ["all", "obvodny", "moskovsky"],
      "period": "date_range",
      "article": "string_or_list",
      "article_kind": ["payment_total", "income_total", "balance_start", "balance_end", "detail"]
    }
  },
  "roadmap": {
    "status": "planned",
    "projects": ["all", "obvodny", "moskovsky", "evgenievsky"],
    "metrics": [],
    "dimensions": [],
    "group_by": [],
    "filters": {}
  },
  "sales_report": {
    "status": "planned",
    "projects": ["all", "obvodny", "moskovsky", "evgenievsky"],
    "metrics": [],
    "dimensions": [],
    "group_by": [],
    "filters": {}
  },
  "sales_plan_execution": {
    "status": "planned",
    "projects": ["all", "obvodny", "moskovsky", "evgenievsky"],
    "metrics": [],
    "dimensions": [],
    "group_by": [],
    "filters": {}
  },
  "agents_report": {
    "status": "planned",
    "projects": ["all", "obvodny", "moskovsky", "evgenievsky"],
    "metrics": [],
    "dimensions": [],
    "group_by": [],
    "filters": {}
  },
  "stock_for_sale": {
    "status": "planned",
    "projects": ["all", "obvodny", "moskovsky", "evgenievsky"],
    "metrics": [],
    "dimensions": [],
    "group_by": [],
    "filters": {}
  },
  "debt_and_bookings": {
    "status": "planned",
    "projects": ["all", "obvodny", "moskovsky", "evgenievsky"],
    "metrics": [],
    "dimensions": [],
    "group_by": [],
    "filters": {}
  },
  "non_project_expenses": {
    "status": "planned",
    "projects": ["all", "obvodny", "moskovsky", "evgenievsky"],
    "metrics": [],
    "dimensions": [],
    "group_by": [],
    "filters": {}
  }
}
```

Правило чтения карты:

```text
report_type выбирает раздел данных
project ограничивает проект или оставляет all
metrics выбирают числовые значения для расчета
dimensions выбирают справочные списки без расчета
group_by задает детализацию результата
filters ограничивают строки перед расчетом
```

Правило обновления контекста:

```text
data_query начинает новый запрос и сбрасывает старый контекст запроса
dimension_query начинает новый запрос и сбрасывает старый контекст запроса
context_query сохраняет старый контекст и применяет только новые поля
если период не указан в новом data_query или dimension_query, используется весь доступный период
если пользователь пишет "за весь период", "за все время" или "без периода", LLM возвращает period.mode = all
если меняется report_type, очищаются period, metrics, dimension, filters, group_by, sort, limit
если приходит dimension, очищаются metrics и group_by
если приходят metrics, очищается dimension
metrics и group_by могут работать вместе для детального отчета
значения одного уровня перезаписывают прошлое актуальное значение
```

## Словарь для ии

### `intent`

```text
data_query - новый запрос к данным
dimension_query - запрос списка значений поля
context_query - уточнение прошлого запроса
math_on_last_result - расчет по последнему результату
clarification_answer - ответ на уточняющий вопрос бота
general_question - общий вопрос без расчета данных
unsupported - неподдерживаемый запрос
```
Тут верхний тип данных не планируется расширять список полный

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
`report_type` - ключ маршрутизации запроса к нужному разделу данных. Список считается стабильным, расширение маловероятно.

Если в сессии и в новом сообщении нет `report_type`, бот не подставляет тип отчета сам и задает уточнение.

Понимание пользовательских формулировок настраивается через aliases:

```text
summary - сводный отчет, сводка, общий отчет
model - модель, финансовая модель
payment_calendar - платежный календарь, платежи, план факт платежей, отклонение по платежам
roadmap - дорожная карта, roadmap, роадмап
sales_report - отчет о продажах, продажи, выручка, сделки, квадратные метры
sales_plan_execution - исполнение плана продаж, план продаж, выполнение плана продаж
agents_report - отчет по агентам, агенты, агентское вознаграждение
stock_for_sale - остатки в продаже, остатки, склад, экспозиция
debt_and_bookings - ДЗ и брони, ДЗ, дебиторка, долги, брони, бронирования
non_project_expenses - непроектные расходы, расходы вне проекта, общие расходы
```

### `project`

```text
obvodny - Обводный
moskovsky - Московский
evgenievsky - Евгеньевский
all - все проекты
```

Если проект не указан, backend ставит `project = all`.

Список считается стабильным: отдельное `unknown` для проекта не используется.

### `metric`

```text
plan - план
fact - факт
deviation - отклонение
```

Сейчас активны только метрики платежного календаря. Остальные метрики будут добавляться по мере подключения новых таблиц к БД.

### `dimension`

```text
article - статьи платежного календаря
article_kind - типы строк платежного календаря
project - проекты
period_month - месяцы
```

`dimension` используется для запросов без расчета суммы: например, "какие статьи расходов есть?".

### `group_by`

```text
project - по проектам
period - по периоду
month - по месяцам
article - по статьям
article_kind - по типам строк
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
    "report_type": "payment_calendar",
    "project": "obvodny",
    "period": {
      "from": "2026-03-01",
      "to": "2026-03-31",
      "label": "март 2026"
    },
    "metrics": ["fact"],
    "filters": {
      "article_kind": "payment_total"
    },
    "group_by": []
  },
  "operation": null,
  "needs_clarification": false,
  "clarification_question": null,
  "confidence": 0.95
}
```

Пример запроса списка статей:

```json
{
  "intent": "dimension_query",
  "state_delta": {
    "report_type": "payment_calendar",
    "project": "obvodny",
    "dimension": "article",
    "filters": {
      "article_kind": "detail"
    }
  },
  "operation": null,
  "needs_clarification": false,
  "clarification_question": null,
  "confidence": 0.9
}
```

Пример подробного отчета за месяц:

```json
{
  "intent": "data_query",
  "state_delta": {
    "report_type": "payment_calendar",
    "project": "obvodny",
    "period": {
      "from": "2026-05-01",
      "to": "2026-05-31",
      "label": "май 2026"
    },
    "metrics": ["plan", "fact", "deviation"],
    "filters": {
      "article_kind": "detail"
    },
    "group_by": ["article"]
  },
  "operation": null,
  "needs_clarification": false,
  "clarification_question": null,
  "confidence": 0.9
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
      "metric": "fact"
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
    "metrics": ["fact"]
  },
  "operation": null,
  "needs_clarification": true,
  "clarification_question": "Уточните тип отчета для расчета факта.",
  "confidence": 0.7
}
```

Если нужно сбросить период:

```json
{
  "intent": "context_query",
  "state_delta": {
    "period": {
      "mode": "all"
    }
  },
  "operation": null,
  "needs_clarification": false,
  "clarification_question": null,
  "confidence": 0.9
}
```

## QueryFrame

`QueryFrame` собирается после Context Resolver.

Он не строит SQL и не считает данные. Его задача - понять, готов ли запрос к предметной проверке и дальнейшей компиляции.

### Defaults

```text
report_type не подставляется автоматически
project = all
period.label = весь доступный период
```

### JSON-формат QueryFrame

```json
{
  "intent": "data_query",
  "report_type": "payment_calendar",
  "project": "obvodny",
  "period": {
    "from": "2026-03-01",
    "to": "2026-03-31",
    "label": "март 2026"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {},
  "group_by": ["month"],
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
  "report_type": null,
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "весь доступный период"
  },
  "metrics": [],
  "dimension": null,
  "filters": {},
  "group_by": [],
  "operation": null,
  "ready": false,
  "missing_fields": ["report_type", "metrics"],
  "clarification_question": "Я должен понимать, какой тип отчета вас интересует, чтобы верно достать информацию..."
}
```

Для математики:

```json
{
  "intent": "math_on_last_result",
  "report_type": null,
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "весь доступный период"
  },
  "metrics": [],
  "dimension": null,
  "filters": {},
  "group_by": [],
  "operation": {
    "type": "divide",
    "left": {
      "source": "last_result",
      "metric": "fact"
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
  "group_by": ["period", "month", "metric", "article", "article_kind"],
  "filters": ["project", "period", "metric", "article", "article_kind"],
  "projects": ["all", "obvodny", "moskovsky"],
  "privacy": "safe_aggregate"
}
```

### Текущий каталог

```text
payment_calendar
  plan
  fact
  deviation
```

Остальные `report_type` сейчас известны словарю, но в `MetricCatalog` не имеют активных метрик до подключения их таблиц к БД.

## DomainResolver

`DomainResolver` работает после `QueryFrame` и до `MetricResolution`.

Он не доверяет свободным строкам из LLM как готовым значениям для SQL. Например `filters.article = "реклама"` считается поисковой фразой, а не точным названием статьи.

Общие проверки для `payment_calendar`:

```text
project должен существовать в payment_calendar_facts
если project = all, проверка конкретного проекта не нужна
period проверяется по доступным period_month
если пользователь указал день внутри месяца, период расширяется до всего месяца
если за период нет данных, бот задает уточнение и показывает доступные периоды
```

Правила для `payment_calendar.article`:

```text
поиск идет по реальным article из payment_calendar_facts
регистр, лишние пробелы и ё/е не важны
поддерживается частичное совпадение и простые опечатки
0 совпадений - уточнение, что статья не найдена
1 совпадение - article заменяется на точное значение из БД
2-3 совпадения - article становится списком, добавляется group_by=article
больше 3 совпадений - уточнение у пользователя
```

Пример:

```json
{
  "filters": {
    "article_kind": "detail",
    "article": "реклама"
  }
}
```

После нормализации:

```json
{
  "filters": {
    "article_kind": "detail",
    "article": ["Реклама", "Реклама и маркетинг"]
  },
  "group_by": ["article"]
}
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
      "name": "fact",
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

LLM не пишет SQL напрямую. Таблицы, колонки, выражения метрик, группировки и фильтры берутся только из белых списков внутри `app/pipeline/sql_compiler.py`.

### Правила

```text
QueryFrame должен быть ready=true
MetricResolution должен быть valid=true
operation не компилируется в SQL
metrics не должны быть пустыми для data_query
dimension не должен быть пустым для dimension_query
таблица выбирается по report_type
колонки выбираются по metric, group_by и filters
списки значений выбираются по dimension
значения идут только через params
```

### JSON-формат SQLQuery

```json
{
  "sql": "SELECT\n  period_month AS month,\n  SUM(fact_amount) AS fact\nFROM payment_calendar_facts\nWHERE project = :project\nGROUP BY period_month",
  "params": {
    "project": "obvodny"
  },
  "table": "payment_calendar_facts",
  "metrics": ["fact"],
  "group_by": ["month"]
}
```

Для списка статей:

```json
{
  "sql": "SELECT DISTINCT\n  article AS article\nFROM payment_calendar_facts\nWHERE project = :project\n  AND article_kind = :filter_article_kind\nORDER BY article",
  "params": {
    "project": "obvodny",
    "filter_article_kind": "detail"
  },
  "table": "payment_calendar_facts",
  "metrics": [],
  "group_by": ["article"]
}
```

### Текущие SQL-шаблоны

```text
payment_calendar -> payment_calendar_facts
```

Сейчас активен только SQL-шаблон платежного календаря. Остальные типы отчетов будут подключаться сюда после появления их таблиц в БД.

## Первый слой данных

Сейчас подключен первый реальный слой: `payment_calendar` для проектов `moskovsky` и `obvodny`.

Источник:

```text
../оригиналы таблиц/платежный календарь/ооо велл
../оригиналы таблиц/платежный календарь/обводный 118
```

Таблица:

```text
payment_calendar_facts
  id - технический id
  project - проект, сейчас moskovsky
  period_month - месяц отчета
  article - статья платежного календаря
  article_kind - тип статьи для безопасных расчетов
  article_order - порядок строки в исходном месяце
  plan_amount - план
  fact_amount - факт
  deviation_amount - отклонение
  source_file - файл-источник
  created_at - дата загрузки строки
```

Команда импорта:

```bash
python -m app.importers.payment_calendar --project moskovsky --source "../оригиналы таблиц/платежный календарь/ооо велл"
python -m app.importers.payment_calendar --project obvodny --source "../оригиналы таблиц/платежный календарь/обводный 118"
```

Правила импорта:

```text
читаются все .xlsx внутри папки источника
строка месяца берется из C2
статья берется из B
план берется из C
факт берется из D
отклонение берется из E
комментарии из таблиц не импортируются
повторный импорт заменяет строки тех же месяцев и проекта
```

Типы строк:

```text
payment_total - ИТОГО платежи
income_total - Поступления
balance_start - Остаток ДС на начало месяца
balance_end - Остаток ДС на конец месяца
detail - обычная детальная строка
```

Правило расчета:

```text
общая сумма платежей берется по article_kind = payment_total
общая сумма поступлений берется по article_kind = income_total
остатки берутся по balance_start или balance_end
детализация берется по article_kind = detail
```

### Ошибки SQLCompiler

```text
query_frame_not_ready - QueryFrame еще не готов
metric_resolution_not_valid - метрики не прошли проверку
operation_query_not_supported - это расчет по последнему результату, не SQL-запрос
empty_metrics - нет метрик для SELECT
empty_dimension - нет dimension для SELECT DISTINCT
unknown_report_type - нет SQL-шаблона для типа отчета
unknown_metric - нет SQL-выражения для метрики
unknown_dimension - нет SQL-колонки для списка значений
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
      "project": "obvodny",
      "fact": 150.26
    }
  ],
  "row_count": 1,
  "metrics": ["fact"],
  "columns": ["project", "fact"],
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
      "metric": "fact"
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
  "metrics": ["fact"],
  "columns": ["project", "fact"],
  "source": {
    "report_type": "payment_calendar",
    "project": "obvodny",
    "period": {
      "from": null,
      "to": null,
      "label": "весь доступный период"
    },
    "metrics": ["fact"],
    "units": {
      "fact": "rub"
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
  "plan": "allowed",
  "fact": "allowed",
  "deviation": "allowed",
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
  "title": "Факт: payment_calendar, obvodny",
  "summary": [
    {
      "metric": "fact",
      "label": "Факт",
      "value": 150.26,
      "unit": "руб."
    }
  ],
  "table": {
    "columns": ["project", "fact"],
    "rows": [
      {
        "project": "obvodny",
        "fact": 150.26
      }
    ],
    "total_rows": 1,
    "truncated": false
  },
  "source": {
    "report_type": "payment_calendar",
    "project": "obvodny",
    "period": {
      "from": null,
      "to": null,
      "label": "весь доступный период"
    },
    "metrics": ["fact"],
    "units": {
      "fact": "rub"
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

## PDFReport

`PDFReport` работает после `ResponseData` и до `LLMAnswer`.

Правило доставки:

```text
короткий отчет - текстовый ответ через LLMAnswer
большой табличный отчет, больше 30 строк - PDF без LLMAnswer
перед PDF бот отправляет сообщение: "Отчет слишком большой, оформлю вам PDF."
PDF строится из CalculationResult, без обрезки ResponseData.table
```

PDF содержит:

```text
заголовок отчета
проект и период
количество строк
таблицу результата
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
  "text": "Факт по платежному календарю проекта Обводный составил 150.26 руб.",
  "used_metrics": ["fact"],
  "source": {
    "report_type": "payment_calendar",
    "project": "obvodny"
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
    "report_type": "payment_calendar",
    "project": "obvodny",
    "period": {
      "from": null,
      "to": null,
      "label": "весь доступный период"
    },
    "metrics": ["fact"],
    "filter_names": ["article_kind"],
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
