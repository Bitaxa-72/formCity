# Схема работы контекста

Документ фиксирует целевое поведение контекста. По нему проверяем код, admin debug и будущие тесты.

## 1. Тело контекста

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
  "clarification_target": null,
  "clarification_base_state": null
}
```

Смысл полей:

```text
report_type - тип отчета
project - проект, по умолчанию all
period - временной фильтр
metrics - числовые показатели для расчета
dimension - справочный список без расчета
filters - уточняющие фильтры
group_by - группировка результата
sort - сортировка
limit - ограничение строк
last_intent - последнее намерение
awaiting_clarification - бот ждет уточнение
clarification_target - вопрос, на который ждет ответ
clarification_base_state - снимок контекста до уточнения
```

## 2. Главная цепочка

```text
Telegram message
-> LLMInput
-> LLMParsedResponse
-> ContextResolver
-> QueryFrame
-> DomainResolver
-> MetricResolution
-> SQLQuery
-> CalculationResult
-> ResultVerification
-> ResponseData
-> AnswerDraft
-> TelegramResponseStatus
```

Контекст меняется только на этапе `ContextResolver`. Следующие этапы могут нормализовать рабочий запрос, но не должны молча ломать сохраненный смысл.

## 3. Уровни дерева

```text
1. report_type
2. project
3. period
4. metrics или dimension
5. filters
6. group_by
7. sort/limit
```

`metrics` и `dimension` конфликтуют. Если выбран расчет по метрикам, `dimension` очищается. Если выбран справочный список, `metrics` очищаются.

`filters` не конфликтуют с `metrics`. Пример: `metrics=["fact"]` и `filters.article="Реклама"` должны жить вместе.

`period` не является метрикой. Это отдельный фильтр времени.

## 4. Общие правила очистки

```text
Новый data_query или dimension_query:
  начинается с пустого контекста, если есть report_type или нет прошлого report_type.
  применяется поверх прошлого контекста, если report_type не указан, но прошлый report_type есть.

Уточнение:
  применяется поверх предыдущего контекста.
  если есть clarification_base_state, применяется поверх него.

Частичный новый запрос без metrics:
  если бот не ждет уточнение,
  прошлый report_type = payment_calendar,
  пользователь меняет project, period или filters,
  то metrics становятся ["plan", "fact", "deviation"].
  Старую metrics из прошлого запроса не наследуем.

Смена report_type:
  очищает project, period, metrics, dimension, filters, group_by, sort, limit.

Смена report_type в режиме уточнения:
  дополняет контекст и не очищает period, metrics, filters.

Смена metrics:
  очищает dimension.

Смена dimension:
  очищает metrics и group_by.

Смена filters:
  обновляет только указанные фильтры.

Смена period:
  обновляет только период.

Общий вопрос:
  не меняет рабочий контекст.

Математика по последнему результату:
  не меняет основной контекст, добавляет pending_operation.
```

## 5. Период

Если в новом запросе период не указан, backend должен поставить весь доступный период.

```json
{
  "period": {
    "from": null,
    "to": null,
    "label": "весь доступный период"
  }
}
```

Исключение: если бот ждет уточнение, отсутствие периода в ответе пользователя не должно стирать уже выбранный период.

## 6. Новый полный запрос

Сообщение:

```text
платежный календарь факт по рекламе за май
```

LLM должна вернуть смысл:

```json
{
  "intent": "data_query",
  "state_delta": {
    "report_type": "payment_calendar",
    "project": "all",
    "period": {
      "label": "май"
    },
    "metrics": ["fact"],
    "filters": {
      "article": "реклама"
    }
  },
  "needs_clarification": false
}
```

Контекст после `ContextResolver`:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "май"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {
    "article": "реклама"
  },
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

После `DomainResolver` рабочий `QueryFrame` должен заменить свободный текст статьи на точное значение из БД:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": "2026-05-01",
    "to": "2026-05-31",
    "label": "май"
  },
  "metrics": ["fact"],
  "filters": {
    "article": "Реклама"
  },
  "ready": true
}
```

## 7. Новый запрос без периода

Сообщение:

```text
платежный календарь факт по рекламе
```

Если `project = all` и запрос считает метрики, результат должен идти в разрезе проектов:

```json
{
  "project": "all",
  "group_by": ["project"]
}
```

Это правило не дает смешивать проекты в одну сумму.

Контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "весь доступный период"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {
    "article": "реклама"
  },
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

## 8. Запрос с нехваткой метрики

Сообщение:

```text
платежный календарь март итоги
```

Если `итоги` еще не настроены как пакет метрик, LLM может вернуть:

```json
{
  "intent": "data_query",
  "state_delta": {
    "report_type": "payment_calendar",
    "project": "all",
    "period": {
      "label": "март"
    }
  },
  "needs_clarification": false
}
```

Контекст после `ContextResolver`:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "март"
  },
  "metrics": [],
  "dimension": null,
  "filters": {},
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

`QueryFrame` видит, что нет `metrics`, и включает уточнение:

```json
{
  "ready": false,
  "missing_fields": ["metrics"],
  "clarification_question": "Уточните метрику для запроса."
}
```

Сохраненный контекст должен стать:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "март"
  },
  "metrics": [],
  "dimension": null,
  "filters": {},
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": true,
  "clarification_target": "Уточните метрику для запроса."
}
```

## 9. Ответ на уточнение

Предыдущий контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "март"
  },
  "metrics": [],
  "dimension": null,
  "filters": {},
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": true,
  "clarification_target": "Уточните метрику для запроса."
}
```

Сообщение:

```text
факт по рекламе
```

LLM должна вернуть:

```json
{
  "intent": "clarification_answer",
  "state_delta": {
    "metrics": ["fact"],
    "filters": {
      "article": "реклама"
    }
  },
  "needs_clarification": false
}
```

Контекст после `ContextResolver`:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "март"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {
    "article": "реклама"
  },
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "clarification_answer",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

Это ключевое правило: уточнение не начинает новый запрос и не стирает `report_type`, `project`, `period`.

## 10. Уточнение только метрики

Предыдущий контекст тот же, но пользователь пишет:

```text
факт
```

Контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "март"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {},
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "clarification_answer",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

В этом варианте фильтра по статье нет, поэтому расчет идет по всем статьям за март. Это допустимо только если пользователь не писал статью в уточнении.

## 11. Смена типа отчета

Предыдущий контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": "2026-05-01",
    "to": "2026-05-31",
    "label": "май"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {
    "article": "Реклама"
  },
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

Сообщение:

```text
отчет о продажах март итоги
```

Контекст должен стать новым и не должен наследовать статью `Реклама`:

```json
{
  "report_type": "sales_report",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "март"
  },
  "metrics": [],
  "dimension": null,
  "filters": {},
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

Если для `sales_report` еще нет метрик и SQL, backend должен ответить понятным отказом или уточнением, а не считать платежный календарь.

## 12. Смена проекта в текущем контексте

Предыдущий контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "moskovsky",
  "period": {
    "from": "2026-05-01",
    "to": "2026-05-31",
    "label": "май"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {
    "article": "Реклама"
  },
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

## 12.1 Частичный расчет поверх прошлого контекста

Предыдущий контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": "2026-03-01",
    "to": "2026-03-31",
    "label": "март"
  },
  "metrics": ["plan", "fact", "deviation"],
  "dimension": null,
  "filters": {},
  "group_by": ["project"],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null,
  "clarification_base_state": null
}
```

## 12.2 Частичный запрос без метрики

Предыдущий контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": "2026-03-01",
    "to": "2026-03-31",
    "label": "март"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {
    "article": "реклама"
  },
  "group_by": ["project"],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null,
  "clarification_base_state": null
}
```

Сообщение:

```text
Московский агентские вознаграждения май
```

LLM может вернуть новые project, period и article, но без metrics:

```json
{
  "intent": "data_query",
  "state_delta": {
    "project": "moskovsky",
    "period": {
      "label": "май"
    },
    "filters": {
      "article": "агентские вознаграждения"
    }
  },
  "needs_clarification": false
}
```

Такой запрос считается новым частичным запросом, а не уточнением. Старый `fact` не наследуется. Для платежного календаря backend ставит все базовые метрики:

```json
{
  "report_type": "payment_calendar",
  "project": "moskovsky",
  "period": {
    "from": null,
    "to": null,
    "label": "май"
  },
  "metrics": ["plan", "fact", "deviation"],
  "dimension": null,
  "filters": {
    "article": "агентские вознаграждения"
  },
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null,
  "clarification_base_state": null
}
```

Сообщение:

```text
факт по рекламе
```

LLM может вернуть `data_query` без `report_type`:

```json
{
  "intent": "data_query",
  "state_delta": {
    "metrics": ["fact"],
    "filters": {
      "article": "реклама"
    }
  },
  "needs_clarification": false
}
```

Backend не должен начинать пустой контекст, потому что прошлый `report_type` есть. Итог:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": "2026-03-01",
    "to": "2026-03-31",
    "label": "март"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {
    "article": "реклама"
  },
  "group_by": ["project"],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null,
  "clarification_base_state": null
}
```

Сообщение:

```text
а по обводному?
```

LLM должна вернуть `context_query`, а не новый `data_query`:

```json
{
  "intent": "context_query",
  "state_delta": {
    "project": "obvodny"
  },
  "needs_clarification": false
}
```

Контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "obvodny",
  "period": {
    "from": "2026-05-01",
    "to": "2026-05-31",
    "label": "май"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {
    "article": "Реклама"
  },
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "context_query",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

## 13. Список значений

Сообщение:

```text
какие статьи расходов есть в платежном календаре?
```

Контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "весь доступный период"
  },
  "metrics": [],
  "dimension": "article",
  "filters": {
    "article_kind": "detail"
  },
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "dimension_query",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

Если после этого пользователь пишет:

```text
факт по рекламе за май
```

Контекст должен перейти обратно в расчет:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "май"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {
    "article": "реклама"
  },
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

## 14. Детальный отчет

Сообщение:

```text
план факт отклонение по статьям за май
```

Контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "май"
  },
  "metrics": ["plan", "fact", "deviation"],
  "dimension": null,
  "filters": {
    "article_kind": "detail"
  },
  "group_by": ["article"],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

Здесь `metrics` и `group_by` работают вместе. Это не `dimension_query`, потому что пользователь просит расчетные значения.

## 15. Математика по последнему результату

Предыдущий запрос уже вернул результат. Пользователь пишет:

```text
подели последний факт на два
```

Контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "май"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {
    "article": "Реклама"
  },
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "math_on_last_result",
  "awaiting_clarification": false,
  "clarification_target": null,
  "pending_operation": {
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

Основной контекст не должен очищаться, потому что математика использует последний результат.

## 16. Общий вопрос

Сообщение:

```text
привет
```

Контекст не меняется:

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

Backend должен отправить общий ответ без SQL.

## 17. Неподдерживаемый запрос

Сообщение:

```text
нарисуй картинку
```

Контекст не должен превращаться в рабочий запрос:

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
  "last_intent": "unsupported",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

Backend должен ответить, что такой запрос не поддерживается.

## 18. Ошибочная широкая выдача

Этот сценарий запрещен.

Пользователь:

```text
платежный календарь март итоги
```

Бот:

```text
Уточните метрику для запроса.
```

Пользователь:

```text
факт по рекламе
```

Правильный итоговый контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "март"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {
    "article": "реклама"
  },
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "clarification_answer",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

Неправильный итоговый контекст:

```json
{
  "report_type": "payment_calendar",
  "project": "all",
  "period": {
    "from": null,
    "to": null,
    "label": "весь доступный период"
  },
  "metrics": ["fact"],
  "dimension": null,
  "filters": {},
  "group_by": [],
  "sort": null,
  "limit": null,
  "last_intent": "data_query",
  "awaiting_clarification": false,
  "clarification_target": null
}
```

Такой контекст приводит к расчету всего факта по всей таблице. Backend должен либо не допускать такую потерю, либо явно спросить уточнение перед SQL.

## 19. Критерии корректности

```text
1. Если бот ждет уточнение, новый ответ пользователя не должен стирать старый period/report_type/project.
2. Если пользователь в уточнении добавил article, он обязан попасть в filters.article.
3. Если metrics пустые, SQL не запускается.
4. Если report_type не поддержан данными, SQL не запускается.
5. Если фильтр из текста не попал в QueryFrame, backend не должен делать широкий расчет без предупреждения.
6. Если период не указан в новом самостоятельном запросе, используется весь доступный период.
7. Если период не указан в уточнении, старый период сохраняется.
8. Если сменился report_type, старые filters и metrics не наследуются.
9. Если пришел general_question, рабочий контекст не меняется.
10. Если пришел unsupported, рабочий расчет не запускается.
```

## 20. Что надо проверить тестами

```text
1. data_query полный
2. data_query без периода
3. data_query без metrics -> clarification
4. clarification_answer сохраняет period
5. clarification_answer добавляет filters.article
6. context_query меняет project без сброса остального
7. dimension_query очищает metrics
8. data_query после dimension_query очищает dimension
9. report_type change очищает нижние уровни
10. general_question не меняет state
11. unsupported не запускает SQL
12. широкий расчет после уточнения блокируется
```
