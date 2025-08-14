# Testing Troubleshooting Guide

**Version**: 1.0  
**Last Updated**: January 25, 2025  
**Purpose**: Руководство по решению проблем при тестировании TD Bot

## Overview

Этот документ описывает типичные проблемы, с которыми можно столкнуться при разработке и запуске тестов для Tres Dias Israel Telegram Bot, и способы их решения.

## Common Issues and Solutions

### 1. Framework Compatibility Issues

#### Problem: pytest vs unittest
**Симптом**: Использование pytest синтаксиса в проекте, который использует unittest

**Error Example**:
```bash
/Library/Developer/CommandLineTools/usr/bin/python3: No module named pytest
```

**Root Cause**: Проект использует стандартный Python unittest, а не pytest

**Solution**:
1. **Используйте unittest синтаксис**:
   ```python
   import unittest
   
   class TestExample(unittest.TestCase):  # Наследование от unittest.TestCase
       def setUp(self):                   # НЕ setup_method()
           pass
       
       def tearDown(self):                # НЕ teardown_method()
           pass
       
       def test_something(self):
           self.assertEqual(a, b)         # НЕ assert a == b
           self.assertTrue(condition)     # НЕ assert condition
   ```

2. **Запуск тестов**:
   ```bash
   # Правильно
   python -m unittest tests.test_module -v
   ./venv/bin/python -m unittest tests.test_module -v
   
   # Неправильно
   python -m pytest tests/test_module.py
   ```

### 2. Virtual Environment Issues

#### Problem: ModuleNotFoundError for installed packages
**Симптом**: Модули не найдены, хотя requirements.txt установлен

**Error Example**:
```bash
ModuleNotFoundError: No module named 'telegram'
```

**Root Cause**: Тесты запускаются с системным Python, а не из виртуального окружения

**Solution**:
1. **Используйте прямой путь к Python в venv**:
   ```bash
   ./venv/bin/python -m unittest tests.test_module -v
   ```

2. **Или активируйте окружение правильно**:
   ```bash
   source venv/bin/activate
   python -m unittest tests.test_module -v
   ```

3. **Проверка активации окружения**:
   ```bash
   which python  # Должен показать путь в venv/
   pip list      # Должен показать установленные пакеты
   ```

### 3. Method Name Mismatches

#### Problem: AttributeError for non-existent methods
**Симптом**: Методы в тестах не соответствуют реальной реализации

**Error Example**:
```bash
AttributeError: 'SqliteParticipantRepository' object has no attribute 'add_participant'
```

**Root Cause**: Неправильные названия методов или неправильное понимание API

**Solution**:
1. **Исследуйте реальные методы**:
   ```bash
   grep -r "def " services/ repositories/ | grep -i payment
   ```

2. **Проверьте существующие тесты**:
   ```bash
   grep -r "add_participant\|create_participant" tests/
   ```

3. **Используйте правильные методы**:
   ```python
   # Неправильно
   participant_id = repository.add_participant(participant)
   
   # Правильно (нужно проверить в коде)
   participant_id = service.add_participant(participant_data)
   ```

### 4. Database Testing Patterns

#### Problem: Database connection issues in tests
**Симптом**: Тесты не могут подключиться к БД или используют production БД

**Root Cause**: Неправильная настройка in-memory database для тестов

**Solution**:
1. **Используйте паттерн из существующих тестов**:
   ```python
   def setUp(self):
       database.DB_PATH = ":memory:"
       self.conn = sqlite3.connect(database.DB_PATH)
       self.conn.row_factory = sqlite3.Row
       
       # Патчим DatabaseConnection
       self._original_enter = database.DatabaseConnection.__enter__
       self._original_exit = database.DatabaseConnection.__exit__
       
       def _enter(_self):
           _self.conn = self.conn
           return self.conn
       
       database.DatabaseConnection.__enter__ = _enter
       database.init_database()
   
   def tearDown(self):
       database.DatabaseConnection.__enter__ = self._original_enter
       database.DatabaseConnection.__exit__ = self._original_exit
       self.conn.close()
   ```

### 5. Data Validation Issues

#### Problem: Tests fail due to incorrect expected values
**Симптom**: AssertionError с различием в ожидаемых данных

**Error Example**:
```bash
AssertionError: {'Paid': 'Оплачено'} != {'Paid': '✅ Оплачено'}
```

**Root Cause**: Неправильные ожидаемые значения в тестах

**Solution**:
1. **Проверьте реальные значения в constants.py**:
   ```python
   from constants import PAYMENT_STATUS_DISPLAY
   print(PAYMENT_STATUS_DISPLAY)
   ```

2. **Обновите тесты с правильными значениями**:
   ```python
   # Используйте реальные значения из кода
   expected_display = PAYMENT_STATUS_DISPLAY  # Вместо hardcoded значений
   ```

### 6. Import Path Issues

#### Problem: ModuleNotFoundError for local modules
**Симптом**: Локальные модули не найдены при запуске тестов

**Solution**:
1. **Запускайте тесты из корневой директории проекта**:
   ```bash
   cd td-event-telegram-bot
   python -m unittest tests.test_module
   ```

2. **Убедитесь в правильной структуре импортов**:
   ```python
   # Правильно
   from models.participant import Participant
   from services.participant_service import ParticipantService
   
   # Неправильно (если запускаете из tests/)
   from ../models.participant import Participant
   ```

## Best Practices for Test Development

### 1. Research Before Writing
```bash
# Исследуйте существующие тесты
ls tests/
grep -r "class.*TestCase" tests/

# Изучите реальные методы
grep -r "def " services/ repositories/

# Проверьте константы и конфигурацию
cat constants.py
```

### 2. Follow Existing Patterns
- Используйте те же паттерны setUp/tearDown что и в других тестах
- Копируйте database mocking из существующих тестов
- Следуйте naming conventions проекта

### 3. Incremental Testing
```bash
# Тестируйте по частям
python -m unittest tests.test_payment_functionality.TestPaymentModel -v

# Затем добавляйте следующий класс
python -m unittest tests.test_payment_functionality.TestPaymentService -v
```

### 4. Validation Testing
```bash
# Проверяйте синтаксис
python -m py_compile tests/test_payment_functionality.py

# Запускайте один тест за раз
python -m unittest tests.test_payment_functionality.TestPaymentModel.test_participant_payment_fields_default_values -v
```

## Quick Debugging Commands

### Check Environment
```bash
# Проверить активацию venv
which python
pip list | grep telegram

# Проверить структуру проекта
ls -la
ls tests/
```

### Inspect Code
```bash
# Найти методы в коде
grep -r "def.*payment" services/ repositories/
grep -r "class.*Repository" repositories/

# Проверить константы
grep -r "PAYMENT_STATUS" constants.py
```

### Test Specific Components
```bash
# Тестировать только модель
python -m unittest tests.test_payment_functionality.TestPaymentModel -v

# Тестировать только один метод
python -m unittest tests.test_payment_functionality.TestPaymentModel.test_participant_payment_fields_default_values -v
```

## Common Error Patterns

### 1. Method Not Found
```
AttributeError: 'Class' object has no attribute 'method_name'
```
**Fix**: Research actual method names in the codebase

### 2. Wrong Expected Values
```
AssertionError: 'actual' != 'expected'
```
**Fix**: Check actual values in constants/config files

### 3. Import Errors
```
ModuleNotFoundError: No module named 'module'
```
**Fix**: Check virtual environment and import paths

### 4. Database Issues
```
sqlite3.OperationalError: no such table
```
**Fix**: Ensure database initialization in setUp()

## Testing Checklist

Before submitting tests:

- [ ] ✅ Tests use unittest.TestCase (not pytest)
- [ ] ✅ Methods follow existing naming patterns
- [ ] ✅ Database mocking follows project patterns
- [ ] ✅ Expected values match actual implementation
- [ ] ✅ All imports are correct
- [ ] ✅ Tests run with ./venv/bin/python
- [ ] ✅ Syntax is validated with py_compile
- [ ] ✅ Individual test classes work before testing all together

## Resources

- **Existing Test Examples**: `tests/test_database.py`, `tests/test_search_engine.py`
- **Project Documentation**: `docs/tests-structure.md`
- **Python unittest Documentation**: https://docs.python.org/3/library/unittest.html

---

*This guide should be updated whenever new testing patterns or issues are discovered.*
