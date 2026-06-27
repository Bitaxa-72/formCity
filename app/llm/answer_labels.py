import json

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.llm.chat_options import build_chat_completion_options
from app.pipeline.response_data import ResponseData


ANSWER_SYSTEM_PROMPT = """
Ты оформляешь проверенные данные backend в короткий русский ответ.
Используй только числа, метрики, таблицы и source из входного JSON.
Не добавляй новые цифры.
Не делай новые расчеты.
Не упоминай SQL, JSON, backend и внутренние этапы.
Верни только валидный JSON.
"""

GENERAL_ANSWER_SYSTEM_PROMPT = """
Ты отвечаешь пользователю коротко по-русски.
Это общий вопрос или приветствие, не запрос к данным.
Не рассчитывай данные.
Не придумывай цифры.
Не упоминай SQL, JSON, backend и внутренние этапы.
Если пользователь здоровается, поздоровайся и кратко скажи, что можешь помочь с отчетами и данными проекта.
Верни только валидный JSON.
"""


class LLMAnswerError(RuntimeError):
    pass


class AnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    used_metrics: list[str] = Field(default_factory=list)
    source: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


GENERAL_FALLBACK_TEXT = (
    "Не понял запрос к данным.\n\n"
    "Укажите, пожалуйста, тип отчета, проект, метрику и период.\n\n"
    "Доступные отчеты:\n"
    "- сводный отчет\n"
    "- модель\n"
    "- платежный календарь\n"
    "- дорожная карта\n"
    "- отчет о продажах\n"
    "- отчет об исполнении плана продаж\n"
    "- отчет по агентам\n"
    "- остатки в продаже\n"
    "- ДЗ и брони\n"
    "- непроектные расходы"
)
CAPABILITIES_TEXT = (
    "Я помогаю получать данные из подключенных отчетов.\n\n"
    "Сейчас подключены:\n\n"
    "Платежный календарь:\n"
    "- проекты: Московский, Обводный;\n"
    "- периоды: февраль 2026, март 2026, апрель 2026, май 2026;\n"
    "- показатели: план, факт, отклонение;\n"
    "- можно смотреть итоги, поступления, платежи, остатки и статьи расходов.\n\n"
    "Дорожная карта:\n"
    "- периоды: февраль 2026, март 2026, апрель 2026;\n"
    "- можно смотреть этапы, сроки этапов, итоговый срок и внешние этапы.\n\n"
    "Модель:\n"
    "- можно смотреть KPI: выручка, себестоимость, валовая прибыль, чистая прибыль, NPV, ROE, LLCR, площадь, помещения, ПИР;\n"
    "- можно смотреть доступные срезы, raw-листы и безопасные строки raw-листов.\n\n"
    "Непроектные расходы:\n"
    "- можно смотреть суммы, исполнение, остатки, статьи и категории расходов.\n\n"
    "Остатки в продаже:\n"
    "- проект: Обводный;\n"
    "- периоды: февраль 2026, март 2026, апрель 2026;\n"
    "- можно смотреть суммы, площадь, количество объектов, цены за м2, типы объектов, этажи и строки в работе.\n\n"
    "Отчет о продажах:\n"
    "- проект: Обводный;\n"
    "- срезы: февраль 2026, март 2026, апрель 2026;\n"
    "- можно смотреть выручку, метры, сделки, цены за м2, оплаты ДДУ, сегменты и месяцы продаж.\n\n"
    "Исполнение плана продаж:\n"
    "- проект: Обводный;\n"
    "- срезы: февраль 2026, март 2026, апрель 2026;\n"
    "- можно смотреть продажи, поступления, площадь, сделки, цену за м2, план, факт, прогноз, отклонения, сегменты и остаток к продаже.\n\n"
    "Отчет по агентам:\n"
    "- проект: Обводный;\n"
    "- можно смотреть сделки, площадь, агентское вознаграждение, оплаты, остаток, суммы ДДУ, уступки, графики оплат, наименования агентов и номера помещений.\n\n"
    "ДЗ и брони:\n"
    "- можно смотреть суммы, планы, факты оплат, остатки, отказы, статусы, секции и номера помещений.\n\n"
    "Сводный отчет:\n"
    "- проекты: Московский, Обводный, Евгеньевский;\n"
    "- можно смотреть доступные листы, строки, колонки, типы листов и безопасные числовые значения.\n\n"
    "Если проект не указан, покажу данные по всем проектам отдельно.\n"
    "Если период не указан для платежного календаря, возьму весь доступный период.\n"
    "Если период не указан для дорожной карты, модели и остатков в продаже, возьму последний актуальный месяц."
)
ROADMAP_UNCLEAR_TEXT = (
    "Не понял запрос по дорожной карте.\n\n"
    "Укажите, что показать:\n"
    "- этапы\n"
    "- сроки этапов\n"
    "- итоговый срок\n"
    "- внешние этапы: банк или Росреестр\n"
    "- доступные периоды"
)

METRIC_LABELS = {
    "plan": "План",
    "fact": "Факт",
    "deviation": "Отклонение",
    "value": "Значение",
    "duration_min": "Минимальный срок",
    "duration_max": "Максимальный срок",
    "duration_range": "Диапазон срока",
    "step_count": "Количество этапов",
    "model_revenue": "\u0412\u044b\u0440\u0443\u0447\u043a\u0430",
    "model_cost_of_sales": "\u0421\u0435\u0431\u0435\u0441\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c \u043f\u0440\u043e\u0434\u0430\u0436",
    "model_gross_profit": "\u0412\u0430\u043b\u043e\u0432\u0430\u044f \u043f\u0440\u0438\u0431\u044b\u043b\u044c",
    "model_net_profit": "\u0427\u0438\u0441\u0442\u0430\u044f \u043f\u0440\u0438\u0431\u044b\u043b\u044c",
    "model_npv": "NPV",
    "model_roe": "ROE",
    "model_llcr": "LLCR",
    "model_total_area": "\u041e\u0431\u0449\u0430\u044f \u043f\u043b\u043e\u0449\u0430\u0434\u044c",
    "model_units_count": "\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043f\u043e\u043c\u0435\u0449\u0435\u043d\u0438\u0439",
    "model_pir": "\u041f\u0418\u0420",
    "amount": "Сумма",
    "executed_amount": "Исполнено",
    "remaining_amount": "Остаток / прогноз",
    "debt_item_count": "Количество строк",
    "debt_total_amount": "Сумма",
    "debt_monthly_value": "Помесячная сумма",
    "debt_plan_amount": "План",
    "debt_updated_plan_amount": "Уточненный план",
    "debt_fact_payment_amount": "Факт оплат",
    "debt_remaining_amount": "Остаток",
    "debt_refusal_count": "Количество отказов",
    "debt_refusal_area": "Площадь отказов",
    "debt_refusal_full_price": "Сумма отказов",
    "stock_ddu_amount": "Сумма ДДУ",
    "stock_dupt_markup_amount": "Наценка ДУПТ",
    "stock_total_amount": "Сумма всего",
    "stock_area_sqm": "Площадь",
    "stock_unit_count": "Количество объектов",
    "stock_ddu_price_per_sqm": "Цена ДДУ за м2",
    "stock_dupt_price_per_sqm": "Цена ДУПТ за м2",
    "stock_total_price_per_sqm": "Цена за м2",
    "sales_contract_revenue": "Выручка по контрактации",
    "sales_contract_area_sqm": "Объем контрактации",
    "sales_contract_count": "Количество сделок",
    "sales_price_per_sqm": "Цена за м2",
    "sales_ddu_actual_payments": "Фактические оплаты по ДДУ",
    "sales_ddu_remaining_payment_schedule": "График оплаты остатка по ДДУ",
    "sales_cumulative_price_per_sqm": "Накопительная цена за м2",
    "sales_plan_revenue": "Продажи",
    "sales_plan_cash_receipts": "Поступления денежных средств",
    "sales_plan_contract_area_sqm": "Площадь контрактации",
    "sales_plan_contract_count": "Количество сделок",
    "sales_plan_price_per_sqm": "Цена за м2",
    "agents_deal_count": "Количество сделок",
    "agents_area_sqm": "Площадь",
    "agents_commission_base_amount": "База вознаграждения",
    "agents_commission_amount": "Агентское вознаграждение",
    "agents_act_total_amount": "Сумма по акту",
    "agents_paid_amount": "Оплачено",
    "agents_remaining_amount": "Остаток к оплате",
    "agents_ddu_assignment_amount": "ДДУ + уступка",
    "agents_ddu_amount": "ДДУ",
    "agents_assignment_amount": "Уступка",
    "agents_furniture_amount": "Меблировка",
    "agents_monthly_value": "Сумма графика",
    "summary_sheet_count": "Количество листов",
    "summary_row_count": "Количество строк",
    "summary_cell_count": "Количество ячеек",
    "summary_numeric_cell_count": "Числовые ячейки",
    "summary_value_sum": "Сумма значений",
}

DIMENSION_LABELS = {
    "project": "Проект",
    "article": "Статья",
    "article_kind": "Раздел",
    "month": "Месяц",
    "period": "Период",
    "period_month": "Месяц",
    "row_order": "Порядок",
    "step": "Этап",
    "snapshot_month": "\u0421\u0440\u0435\u0437\u044b \u043c\u043e\u0434\u0435\u043b\u0438",
    "metric": "\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u0438",
    "parent_step": "Родительский этап",
    "action": "Действие",
    "external": "Внешний этап",
    "total": "Итого",
    "snapshot_month": "\u0421\u0440\u0435\u0437 \u043c\u043e\u0434\u0435\u043b\u0438",
    "metric": "\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u044c",
    "item_kind": "Тип",
    "fm_category": "Категория",
    "item_name": "Строка",
    "row_type": "Вид строки",
    "raw_sheet": "Лист",
    "row_number": "Строка",
    "row_label": "Название",
    "visible_cells": "Ячейки",
    "values_preview": "Значения",
    "snapshot_month": "Срез",
    "source_kind": "Источник",
    "section": "Раздел",
    "unit_number": "Номер помещения",
    "status": "Статус",
    "payment_type": "Способ оплаты",
    "row_label": "Строка",
    "agent": "Агент",
    "property_type": "Тип объекта",
    "floor_number": "Этаж",
    "is_in_work": "В работе",
    "segment": "Сегмент",
    "metric_key": "Показатель",
    "owner_scope": "Владелец",
    "period_kind": "Тип периода",
    "scenario": "Сценарий",
    "budget_month": "Бюджетный месяц",
    "payment_period_month": "Месяц оплаты",
    "value_kind": "График",
    "source_file": "Файл",
    "sheet_name": "Лист",
    "sheet_kind": "Тип листа",
    "header_key": "Колонка",
}

DIMENSION_LIST_LABELS = {
    "article": "Статьи",
    "article_kind": "Разделы",
    "project": "Проекты",
    "period_month": "Периоды",
    "period": "Периоды",
    "month": "Месяцы",
    "step": "Этапы",
    "snapshot_month": "Срезы модели",
    "metric": "Показатели",
    "item_kind": "Типы",
    "fm_category": "Категории",
    "item_name": "Строки",
    "row_type": "Виды строк",
    "raw_sheet": "Листы",
    "snapshot_month": "Срезы",
    "source_kind": "Источники",
    "section": "Разделы",
    "unit_number": "Номера помещений",
    "status": "Статусы",
    "payment_type": "Способы оплаты",
    "row_label": "Строки",
    "agent": "Агенты",
    "property_type": "Типы объектов",
    "floor_number": "Этажи",
    "segment": "Сегменты",
    "metric_key": "Показатели",
    "owner_scope": "Владельцы",
    "period_kind": "Типы периодов",
    "scenario": "Сценарии",
    "budget_month": "Бюджетные месяцы",
    "payment_period_month": "Месяцы оплат",
    "value_kind": "Графики",
    "source_file": "Файлы",
    "sheet_name": "Листы",
    "sheet_kind": "Типы листов",
    "header_key": "Колонки",
}

PROJECT_LABELS = {
    "obvodny": "Обводный",
    "moskovsky": "Московский",
    "evgenievsky": "Евгеньевский",
    "all": "Все проекты",
}

REPORT_LABELS = {
    "model": "\u041c\u043e\u0434\u0435\u043b\u044c",
    "debt_and_bookings": "ДЗ и брони",
    "non_project_expenses": "Непроектные расходы",
    "payment_calendar": "Платежный календарь",
    "roadmap": "Дорожная карта",
    "stock_for_sale": "Остатки в продаже",
    "sales_report": "Отчет о продажах",
    "sales_plan_execution": "Исполнение плана продаж",
    "agents_report": "Отчет по агентам",
    "summary": "Сводный отчет",
}
MODEL_SAFE_METRICS = [
    "model_revenue",
    "model_cost_of_sales",
    "model_gross_profit",
    "model_net_profit",
    "model_npv",
    "model_roe",
    "model_llcr",
    "model_total_area",
    "model_units_count",
    "model_pir",
]
RAW_SHEET_LABELS = {
    "consolidation": "Для консолидации",
    "для консолидации": "Для консолидации",
    "консолидация": "Для консолидации",
    "financial_model": "Финмодель",
    "финмодель": "Финмодель",
    "фин модель": "Финмодель",
    "финансовая модель": "Финмодель",
    "remains": "Остатки",
    "остатки": "Остатки",
    "остаток": "Остатки",
}

ARTICLE_KIND_LABELS = {
    "balance_start": "Остаток на начало",
    "income_total": "Поступления",
    "payment_total": "Итого платежи",
    "balance_end": "Остаток на конец",
    "detail": "Статья расходов",
}

NON_PROJECT_EXPENSES_ITEM_KIND_LABELS = {
    "lost_income": "Недополученные доходы",
    "debt_receivable": "ДЗ",
    "non_project_expenses_total": "Итог непроектных расходов",
    "personal": "Личное",
    "admin_expenses": "АХР",
    "evgenievsky": "ЕВГ",
    "legal_entity": "Юрлица",
    "fit_out": "Отделочные работы",
    "commercial": "Коммерческие расходы",
    "furniture": "Мебелировка",
    "construction": "Строительные работы",
    "developer_maintenance": "Содержание застройщика",
    "object_maintenance": "Содержание объекта и техзаказчик",
    "finance": "Финансовые расходы",
    "pir": "ПИР",
    "other_income_expense": "Прочие доходы и расходы",
    "other": "Прочее",
    "total": "Итого",
    "registered": "Зарегистрировано",
    "overdue": "Просроченные",
    "current": "Текущие",
    "dupt_signed_unregistered": "ДУПТ подписан, не зарегистрирован",
    "booking": "Брони",
    "detail": "Детальные строки",
    "refusal": "Отказы",
}

SOURCE_KIND_LABELS = {
    "items": "Основной лист",
    "monthly": "Помесячные значения",
    "deviations": "Отклонения",
    "refusals": "Отказы",
}

STOCK_PROPERTY_TYPE_LABELS = {
    "total": "Всего",
    "storage": "Кладовые",
    "restaurant": "Ресторан",
    "first_floor": "Первый этаж",
    "apartment": "Апартаменты",
    "developer_balance": "Остаток застройщика",
    "other": "Прочее",
}

SALES_SEGMENT_LABELS = {
    "project_total": "Итого по проекту",
    "apartments": "Апартаменты",
    "commercial_1_floor": "Коммерция 1 этаж",
    "restaurant": "Ресторан",
    "storage": "Кладовки",
    "commercial_2_floor": "Коммерция 2 этаж",
    "sh": "SH",
}

SALES_OWNER_LABELS = {
    "all": "Все",
    "developer": "Застройщик",
    "well": "Велл",
    "well_including": "в т.ч. Велл",
}

SALES_SCENARIO_LABELS = {
    "total": "Итого",
    "fact": "Факт",
    "plan": "План",
    "deviation": "Отклонение",
    "forecast": "Прогноз",
    "fact_forecast": "Факт + прогноз",
    "forecast_deviation": "Отклонение по прогнозу",
    "fact_minus_forecast": "Разница факт - прогноз",
    "fact_actualized_forecast": "Факт + актуализированный прогноз",
    "remaining_to_sell": "Остаток к продаже",
}

SALES_PERIOD_KIND_LABELS = {
    "total": "Итого",
    "month": "Месяц продаж",
    "past_periods_total": "Прошлые периоды",
    "snapshot": "Накопительный блок",
    "year": "Итого год",
    "project_total": "Итого проект",
}

AGENTS_VALUE_KIND_LABELS = {
    "ddu_schedule": "График ДДУ",
    "assignment_schedule": "График уступки",
}

SUMMARY_SHEET_KIND_LABELS = {
    "residential_units": "Жилые помещения",
    "commercial_units": "Коммерческие помещения",
    "storage_units": "Кладовые",
    "contract_termination": "Расторжения",
    "assignment": "Уступки",
    "guaranteed_income": "Гарантированный доход / аренда",
    "timeline": "Даты",
    "class_summary": "Отчет по классам",
    "summary_totals": "Итоговая сводная",
    "sale_purchase_contract": "ДКП",
    "window_agreements": "ДС по окнам",
    "agents": "Агенты",
    "generic": "Прочее",
}

ROW_TYPE_LABELS = {
    "detail": "Детальная строка",
    "summary": "Итоговая строка",
    "total": "Итого",
    "total_with_markup": "Итого с наценкой ДУПТ",
    "category": "Категория",
    "header": "Заголовок",
    "period_group": "Период",
    "group": "Группа",
}

ARTICLE_KIND_ORDER = {
    "balance_start": 0,
    "income_total": 1,
    "payment_total": 2,
    "balance_end": 3,
    "detail": 4,
}

MISSING_METRIC_TEXT = {
    "plan": "план не заполнен",
    "fact": "факт не заполнен",
    "deviation": "отклонение не заполнено",
    "value": "значение не заполнено",
}

MONTH_LABELS = {
    "01": "январь",
    "02": "февраль",
    "03": "март",
    "04": "апрель",
    "05": "май",
    "06": "июнь",
    "07": "июль",
    "08": "август",
    "09": "сентябрь",
    "10": "октябрь",
    "11": "ноябрь",
    "12": "декабрь",
}
