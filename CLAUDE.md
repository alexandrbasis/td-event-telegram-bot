# Инструкция по исправлению ошибки распознавания размера "medium"

## Описание проблемы

**Входные данные:** "Тест Басис тим админ община грейс муж Хайфа от Ирина Цой medium"

**Текущий неправильный результат:**
- Размер: Не указано
- Кто подал: Ирина Цой medium

**Ожидаемый правильный результат:**
- Размер: M
- Кто подал: Ирина Цой

## Причина ошибки

В функции `parse_participant_data` в файле `parsers/participant_parser.py` функция `_extract_submitted_by` выполняется раньше чем `_extract_simple_fields`. Регулярное выражение в `_extract_submitted_by` захватывает "от Ирина Цой medium" целиком, не давая возможности `_extract_simple_fields` обработать слово "medium" как размер одежды.

## Шаги исправления

### Шаг 1: Изменить порядок вызова функций
**Файл:** `parsers/participant_parser.py`
**Функция:** `parse_participant_data`

**Заменить текущий порядок:**
```python
_extract_submitted_by(text, processed_words, data)
_extract_contacts(all_words, processed_words, data)
_extract_simple_fields(all_words, processed_words, data)
_extract_church(all_words, processed_words, data)
_extract_names(all_words, processed_words, data)
```

**На новый порядок:**
```python
_extract_contacts(all_words, processed_words, data)
_extract_simple_fields(all_words, processed_words, data)
_extract_church(all_words, processed_words, data)
_extract_submitted_by(text, processed_words, data)
_extract_names(all_words, processed_words, data)
```

### Шаг 2: Улучшить функцию `_extract_submitted_by`
**Файл:** `parsers/participant_parser.py`
**Функция:** `_extract_submitted_by`

**Заменить текущую реализацию:**
```python
def _extract_submitted_by(text: str, processed_words: set, data: Dict):
    match = re.search(r'от\s+([А-ЯЁA-Z][А-Яа-яёA-Za-z\s]+?)(?:\s*\+|\s*$)', text, re.IGNORECASE)
    if match:
        data['SubmittedBy'] = match.group(1).strip()
        for word in match.group(0).split():
            processed_words.add(word)
```

**На улучшенную версию:**
```python
def _extract_submitted_by(text: str, processed_words: set, data: Dict):
    # Ищем паттерн "от Имя Фамилия", но останавливаемся на уже обработанных словах
    match = re.search(r'от\s+([А-ЯЁA-Z][А-Яа-яёA-Za-z\s]+)', text, re.IGNORECASE)
    if match:
        full_match = match.group(1).strip()
        words = full_match.split()
        
        # Берем только те слова, которые еще не были обработаны
        valid_words = []
        for word in words:
            if word not in processed_words:
                # Проверяем, что это не ключевое слово размера/роли/департамента
                word_upper = word.upper()
                if (word_upper not in SIZES and 
                    word_upper not in [k for keys in ROLE_KEYWORDS.values() for k in keys] and
                    word_upper not in [k for keys in DEPARTMENT_KEYWORDS.values() for k in keys]):
                    valid_words.append(word)
                else:
                    break  # Останавливаемся на первом ключевом слове
        
        if valid_words:
            data['SubmittedBy'] = ' '.join(valid_words)
            # Добавляем в processed_words только валидные слова
            for word in valid_words:
                processed_words.add(word)
            processed_words.add('от')  # Добавляем предлог
```

### Шаг 3: Добавить SIZES в импорты функции
**Файл:** `parsers/participant_parser.py`

Убедиться, что в функции `_extract_submitted_by` есть доступ к константе `SIZES`:

```python
# В начале файла должны быть определены:
SIZES = [
    'XS', 'EXTRA SMALL', 'EXTRASMALL',
    'S', 'SMALL',
    'M', 'MEDIUM',
    'L', 'LARGE',
    'XL', 'EXTRA LARGE', 'EXTRALARGE',
    'XXL', '2XL', 'EXTRA EXTRA LARGE',
    '3XL', 'XXXL'
]
```

### Шаг 4: Создать тест для проверки исправления
**Файл:** `tests/test_parser.py`

Добавить новый тест:

```python
def test_medium_size_not_in_submitted_by(self):
    """Тест проверяет, что 'medium' распознается как размер, а не как часть имени подавшего"""
    text = "Тест Басис тим админ община грейс муж Хайфа от Ирина Цой medium"
    data = parse_participant_data(text)
    
    self.assertEqual(data['FullNameRU'], 'Тест Басис')
    self.assertEqual(data['Gender'], 'M')
    self.assertEqual(data['Size'], 'M')  # medium должен стать M
    self.assertEqual(data['Role'], 'TEAM')
    self.assertEqual(data['Department'], 'Administration')
    self.assertEqual(data['Church'], 'община грейс')
    self.assertEqual(data['CountryAndCity'], 'Хайфа')
    self.assertEqual(data['SubmittedBy'], 'Ирина Цой')  # без 'medium'
```

### Шаг 5: Запустить тест
```bash
cd tests
python test_parser.py
```

## Проверка результата

После внесения изменений входная строка:
```
"Тест Басис тим админ община грейс муж Хайфа от Ирина Цой medium"
```

Должна давать результат:
```
Имя (рус): Тест Басис
Пол: M
Размер: M
Церковь: община грейс
Роль: TEAM
Департамент: Administration
Город: Хайфа
Кто подал: Ирина Цой
```

## Дополнительные улучшения

После основного исправления рекомендуется также:

1. **Добавить логирование** для отладки порядка обработки
2. **Обновить документацию** с примерами правильного распознавания
3. **Добавить больше тестов** с различными комбинациями размеров и имен

## Возможные побочные эффекты

- Убедиться, что изменение порядка не нарушает распознавание других полей
- Проверить работу с пограничными случаями (имена, содержащие ключевые слова)
- Протестировать с различными форматами входных данных