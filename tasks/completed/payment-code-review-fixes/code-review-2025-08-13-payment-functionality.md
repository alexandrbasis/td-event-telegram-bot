# Code Review Report: Payment Functionality (TDB-1)

**Review Date**: 2025-08-13  
**Reviewer**: AI Code Reviewer  
**Task Reference**: `td-event-telegram-bot/tasks/completed/task-2025-01-24-payment-functionality.md`  
**Status**: ❌ NEEDS CHANGES

---

## Executive Summary

Функционал оплаты реализован во всех слоях (модель, БД, репозитории, сервис, парсер, UI c состояниями и команда `/payment`). Однако есть интеграционные несоответствия между слоями и с тестами, которые приведут к ошибкам во время выполнения и падению тестов. Основные проблемы: несовпадение контракта UI ↔ Service, сравнение статусов в неверном регистре, маппинг отображения статусов не соответствует тестам, форматирование карточки участника не совпадает с ожидаемым, несовпадение ключей валидации и несовместимость API репозитория с тестами.

После внесения указанных правок функционал сможет стабильно работать и проходить тесты.

---

## Requirements Compliance

### ✅ Реализовано
- Расширение модели: `PaymentStatus`, `PaymentAmount` (int), `PaymentDate`.
- Обновление схемы SQLite и миграция для новых полей.
- Методы репозитория: `update_payment`, `get_unpaid_participants`, `get_payment_summary`.
- Сервисный слой: обработка платежа, валидация, статистика.
- Парсер: поддержка полей оплаты в шаблоне и свободном тексте.
- UI: кнопка, состояния, команда `/payment`.

### ❌ Требует доработок
- Отображение статусов оплаты (эмодзи + текст) и fallback при парсинге.
- Единый и корректный контракт между UI и Service для `process_payment`.
- Сравнение значений статусов (используются неверные строковые значения).
- Форматирование карточки участника (ожидаемые строки в тестах).
- Совместимость API репозитория с существующими тестами.
- Единая политика доступа к оплатам и согласование с документацией.

---

## Issues Found (Critical)

1) Несовпадение контракта UI ↔ Service для `process_payment`
- UI ожидает dict с `{"success": True}` и не передаёт `payment_date`.
- Service: `process_payment(participant_id, amount, payment_date, user_id=None) -> bool`.
- Файлы: `main.py`, `services/participant_service.py`
- Риск: Ошибка в обработчике подтверждения, платеж не сохранится.

2) Неверные сравнения значений статуса оплаты
- Используются `'PAID'/'PARTIAL'/'REFUNDED'` вместо фактических `"Paid"/"Partial"/"Refunded"`.
- Файлы: `main.py`, `services/participant_service.py`
- Риск: Неверное отображение статуса оплаты, всегда ветка "не оплачено".

3) `PAYMENT_STATUS_DISPLAY` и fallback не соответствуют тестам/спецификации
- Ожидается:
  - `Unpaid` → `"❌ Не оплачено"`
  - `Paid` → `"✅ Оплачено"`
  - `Partial` → `"🔶 Частично оплачено"`
  - `Refunded` → `"🔄 Возвращено"`
- Функция `payment_status_from_display` должна по умолчанию возвращать `"Unpaid"` при неизвестном вводе.
- Файл: `constants.py`
- Риск: Расхождение отображения/парсинга, падение тестов.

4) `format_participant_block` не совпадает с ожидаемыми строками в тестах
- Тесты ожидают:
  - `"💰 Статус оплаты: ✅ Оплачено"`
  - `"💳 Сумма оплаты: 500 ₪"`
  - `"📅 Дата оплаты: 2025-01-24"`
- Текущая реализация формирует другой текст и принимает `Dict`, а тесты передают `Participant`.
- Файл: `services/participant_service.py`
- Риск: Падение тестов и несоответствие UI.

5) Несовпадение ключей в валидации
- `validate_payment_data` ожидает `amount/status/date`, а тесты подают `PaymentAmount/PaymentStatus`.
- Файл: `services/participant_service.py`
- Риск: Неверная интерпретация входных данных в тестах/коде.

6) Несовместимость API репозитория с тестами
- Тесты вызывают `add_participant`, `get_participant_by_id`, `update_participant(participant_id, data)`.
- Репозиторий предоставляет `add`, `get_by_id`, `update(Participant)`.
- Файл: `repositories/participant_repository.py`
- Риск: Падение тестов, обратная совместимость нарушена.

7) Политика доступа
- Кнопка "Внести оплату" доступна не-координаторам, тогда как команда `/payment` помечена как координаторская и документация противоречива.
- Файлы: `main.py`, `docs/payment-functionality.md`
- Риск: Несогласованность безопасности/UX.

8) Дата операции
- UI показывает дату в формате `dd.mm.YYYY`, сервис ожидает ISO и дата не передается из UI.
- Файл: `main.py`
- Риск: Ошибки сохранения даты платежа.

---

## Recommendations and Proposed Edits

Ниже перечислены минимальные и безопасные правки по файлам.

### 1) `td-event-telegram-bot/constants.py`
- Обновить маппинг и fallback:
```python
PAYMENT_STATUS_DISPLAY = {
    "Unpaid": "❌ Не оплачено",
    "Paid": "✅ Оплачено",
    "Partial": "🔶 Частично оплачено",
    "Refunded": "🔄 Возвращено",
}

def payment_status_from_display(name: str) -> str:
    return DISPLAY_TO_PAYMENT_STATUS.get(name.strip().lower(), "Unpaid")
```

### 2) `td-event-telegram-bot/services/participant_service.py`
- `process_payment`: сделать `payment_date: Optional[str] = None` и задавать `date.today().isoformat()` при отсутствии. Возвращать `bool` (как сейчас) и логировать.
- `format_participant_block`: принимать `Participant | Dict`, выводить строго:
  - `"💰 Статус оплаты: {PAYMENT_STATUS_DISPLAY[status]}"`
  - `"💳 Сумма оплаты: {amount} ₪"` если `amount > 0`
  - `"📅 Дата оплаты: {PaymentDate}"` если есть
- `format_search_result`: сравнивать с `"Paid"/"Partial"/"Refunded"`.
- `validate_payment_data`: принимать обе схемы ключей и нормализовать:
```python
raw_amount = payment_info.get("amount", payment_info.get("PaymentAmount"))
raw_status = payment_info.get("status", payment_info.get("PaymentStatus", "Paid"))
raw_date = payment_info.get("date", payment_info.get("PaymentDate", ""))
```

### 3) `td-event-telegram-bot/repositories/participant_repository.py`
- Добавить тонкие алиасы для обратной совместимости в `SqliteParticipantRepository`:
```python
def add_participant(self, participant: Participant) -> int:
    return self.add(participant)

def get_participant_by_id(self, participant_id: Union[int, str]) -> Optional[Participant]:
    return self.get_by_id(participant_id)

def update_participant(self, participant_id: Union[int, str], data: Dict) -> bool:
    current = self.get_by_id(participant_id)
    if current is None:
        raise ParticipantNotFoundError(f"Participant with id {participant_id} not found")
    updated_dict = asdict(current)
    updated_dict.update({k: v for k, v in data.items() if k in Participant.__annotations__})
    updated = Participant(**updated_dict)
    return self.update(updated)
```

### 4) `td-event-telegram-bot/main.py`
- Везде сравнивать статусы с `"Paid"/"Partial"/"Refunded"`.
- В `handle_payment_confirmation` передавать ISO дату и проверять `bool`:
```python
from datetime import datetime, date
...
payment_date = date.today().isoformat()
success = participant_service.process_payment(participant.id, amount, payment_date, user_id)
if success:
    current_date = datetime.now().strftime("%d.%m.%Y")
    # сообщение об успехе
```
- Ограничить кнопку "Внести оплату" только для координаторов (или обновить документацию, если доступ всем — рекомендуем координаторам).

### 5) `td-event-telegram-bot/docs/payment-functionality.md`
- Обновить секцию доступа к `/payment` в соответствии с принятой политикой (рекомендуется только координаторам).

---

## Testing Plan
- Прогнать тесты: `./venv/bin/python -m unittest discover tests -v`.
- Убедиться, что `tests/test_payment_functionality.py` проходит, в т.ч. форматы строк статуса/суммы/даты.
- Ручной смоук-тест `/payment` в режиме SQLite: ввод суммы → подтверждение → проверка сообщений и обновления БД.

---

## Final Decision

❌ NEEDS FIXES. Внести предложенные правки, затем повторно запустить тесты и предоставить на повторное ревью.
