from app.llm.schema import Dimension, GroupBy, Metric, PaymentCalendarView


RULE: dict[str, object] = {
        "metrics": {
            Metric.SUMMARY_SHEET_COUNT.value: ["количество листов", "сколько листов"],
            Metric.SUMMARY_ROW_COUNT.value: ["количество строк", "сколько строк"],
            Metric.SUMMARY_CELL_COUNT.value: ["количество ячеек", "сколько ячеек"],
            Metric.SUMMARY_NUMERIC_CELL_COUNT.value: ["количество числовых ячеек", "числовые ячейки"],
            Metric.SUMMARY_VALUE_SUM.value: ["сумма", "итого", "сумма значений"],
        },
        "metric_bundles": {
            "overview": {
                "aliases": ["сводный отчет", "сводная", "итоги", "обзор"],
                "metrics": [
                    Metric.SUMMARY_SHEET_COUNT.value,
                    Metric.SUMMARY_ROW_COUNT.value,
                    Metric.SUMMARY_CELL_COUNT.value,
                ],
            },
            "values": {
                "aliases": ["суммы", "числовые значения", "агрегаты"],
                "metrics": [
                    Metric.SUMMARY_NUMERIC_CELL_COUNT.value,
                    Metric.SUMMARY_VALUE_SUM.value,
                ],
            },
        },
        "views": {
            PaymentCalendarView.SUMMARY_OVERVIEW.value: {
                "aliases": ["сводный отчет", "сводная", "обзор сводной", "итоги сводной"],
                "meaning": "безопасный обзор загруженных сводных таблиц",
            },
            PaymentCalendarView.SUMMARY_VALUES.value: {
                "aliases": ["суммы", "числовые значения", "суммы по колонкам", "агрегаты"],
                "meaning": "суммы по безопасным числовым колонкам сводных таблиц",
            },
            PaymentCalendarView.SUMMARY_AVAILABLE_PROJECTS.value: {
                "aliases": ["какие проекты", "список проектов"],
                "meaning": "список проектов в сводных таблицах",
            },
            PaymentCalendarView.SUMMARY_AVAILABLE_FILES.value: {
                "aliases": ["какие файлы", "список файлов", "источники"],
                "meaning": "список файлов-источников сводных таблиц",
            },
            PaymentCalendarView.SUMMARY_AVAILABLE_SHEETS.value: {
                "aliases": ["какие листы", "список листов"],
                "meaning": "список листов сводных таблиц",
            },
            PaymentCalendarView.SUMMARY_AVAILABLE_SHEET_KINDS.value: {
                "aliases": ["типы листов", "виды листов", "разделы"],
                "meaning": "список типов листов сводных таблиц",
            },
            PaymentCalendarView.SUMMARY_AVAILABLE_HEADERS.value: {
                "aliases": ["какие колонки", "какие поля", "какие показатели", "доступные колонки"],
                "meaning": "список безопасных колонок сводных таблиц",
            },
            PaymentCalendarView.SUMMARY_AVAILABLE_ROW_TYPES.value: {
                "aliases": ["типы строк", "виды строк"],
                "meaning": "список типов строк сводных таблиц",
            },
        },
        "filters": {
            Dimension.SHEET_KIND.value: {
                "residential_units": ["апартаменты", "квартиры", "жилье"],
                "commercial_units": ["коммерция", "коммерческие помещения"],
                "storage_units": ["кладовки", "кладовые"],
                "contract_termination": ["расторжения"],
                "assignment": ["уступки"],
                "guaranteed_income": ["гарантированный доход", "аренда"],
                "timeline": ["даты", "таймлайн"],
                "class_summary": ["классы", "по классам"],
                "summary_totals": ["итоговая сводная", "итоги"],
                "sale_purchase_contract": ["дкп"],
                "window_agreements": ["окна"],
                "agents": ["агенты"],
            },
            Dimension.HEADER_KEY.value: {
                "оплачено": ["оплачено", "оплата"],
                "остаток": ["остаток"],
                "площадь": ["площадь", "метры"],
                "цена_1_кв_м": ["цена за метр", "цена м2", "цена 1 кв м"],
                "цена_брони": ["цена брони"],
            },
        },
        "group_by": {
            GroupBy.PROJECT.value: ["по проектам"],
            GroupBy.SHEET_KIND.value: ["по типам листов", "по разделам"],
            GroupBy.SHEET_NAME.value: ["по листам"],
            GroupBy.HEADER_KEY.value: ["по колонкам", "по показателям"],
        },
        "dimensions": {
            Dimension.PROJECT.value: ["какие проекты", "список проектов"],
            Dimension.SOURCE_FILE.value: ["какие файлы", "источники"],
            Dimension.SHEET_NAME.value: ["какие листы", "список листов"],
            Dimension.SHEET_KIND.value: ["типы листов", "виды листов", "разделы"],
            Dimension.HEADER_KEY.value: ["какие колонки", "какие поля", "какие показатели"],
            Dimension.ROW_TYPE.value: ["типы строк", "виды строк"],
        },
    }
