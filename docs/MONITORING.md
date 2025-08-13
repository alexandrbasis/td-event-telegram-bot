# 📊 Мониторинг и логирование

**Version**: 1.0  
**Last Updated**: August 13, 2025 

## Быстрый старт

```bash
# Статистика за сегодня
./scripts/monitor.sh stats

# Следить за активностью в реальном времени
./scripts/monitor.sh live-users

# Проверить ошибки
./scripts/monitor.sh errors
```

## Структура логов

```
logs/
├── bot.log                 # Общие логи приложения
├── errors.log              # Ошибки с полным контекстом
├── user_actions.log        # Действия пользователей (JSON)
├── participant_changes.log # Изменения участников (JSON)
├── performance.log         # Метрики производительности (JSON)
├── sql.log                 # SQL запросы (только ошибки)
└── archive/                # Архив старых логов
```

## Команды мониторинга

### Режим реального времени

```
./scripts/monitor.sh live-users   - действия пользователей
./scripts/monitor.sh live-errors  - ошибки
./scripts/monitor.sh live-changes - изменения участников
```

### Анализ

```
./scripts/monitor.sh stats       - статистика за день
./scripts/monitor.sh user [ID]   - действия пользователя
./scripts/monitor.sh performance - медленные операции
./scripts/monitor.sh report      - HTML отчёт
```

### Обслуживание

```
./scripts/log_cleanup.sh - архивирование старых логов
```

## Поиск и фильтрация

```bash
# Все действия пользователя 12345
grep '"user_id": 12345' logs/user_actions.log | jq .

# Команды /add за сегодня
grep "$(date +%Y-%m-%d)" logs/user_actions.log | grep '"/add"'

# Ошибки валидации
grep "ValidationError" logs/errors.log

# Медленные операции (>2 сек)
cat logs/performance.log | jq 'select(.duration > 2.0)'
```

## Настройка алертов
Добавьте в crontab для ежедневной проверки:

```bash
# Проверка ошибок каждый час
0 * * * * cd /path/to/bot && ./scripts/monitor.sh errors | grep "$(date +%Y-%m-%d)" | wc -l > /tmp/bot_errors_count

# Архивирование логов каждую неделю
0 2 * * 0 cd /path/to/bot && ./scripts/log_cleanup.sh
```

