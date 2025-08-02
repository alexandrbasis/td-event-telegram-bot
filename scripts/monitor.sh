#!/bin/bash
# Скрипт для мониторинга логов бота

LOG_DIR="logs"

# Функции для удобного доступа
show_help() {
    echo "🤖 Tre Dias Israel Bot - Log Monitor"
    echo "Использование: ./scripts/monitor.sh [команда]"
    echo ""
    echo "Команды:"
    echo "  live-users     - Следить за действиями пользователей в реальном времени"
    echo "  live-errors    - Следить за ошибками в реальном времени"
    echo "  live-changes   - Следить за изменениями участников"
    echo "  stats          - Показать статистику за сегодня"
    echo "  errors         - Показать последние ошибки"
    echo "  user [ID]      - Показать действия конкретного пользователя"
    echo "  performance    - Показать медленные операции"
    echo "  report         - Создать HTML отчет"
}

live_users() {
    echo "📱 Следим за действиями пользователей (Ctrl+C для выхода)..."
    tail -f "$LOG_DIR/user_actions.log" | jq --unbuffered -r '
        "\(.timestamp // now | strftime(\"%H:%M:%S\")) | 👤\(.user_id) | \(.action) | \(.details.command // .details | tostring)"
    ' 2>/dev/null || tail -f "$LOG_DIR/user_actions.log"
}

live_errors() {
    echo "🚨 Следим за ошибками (Ctrl+C для выхода)..."
    tail -f "$LOG_DIR/errors.log"
}

live_changes() {
    echo "📝 Следим за изменениями участников (Ctrl+C для выхода)..."
    tail -f "$LOG_DIR/participant_changes.log" | jq --unbuffered -r '
        "\(.timestamp // now | strftime(\"%H:%M:%S\")) | 👤\(.user_id) | \(.operation) | ID:\(.participant_id // \"new\")"
    ' 2>/dev/null || tail -f "$LOG_DIR/participant_changes.log"
}

show_stats() {
    echo "📊 Статистика за сегодня $(date +%Y-%m-%d):"
    today=$(date +%Y-%m-%d)
    
    if [[ -f "$LOG_DIR/user_actions.log" ]]; then
        actions=$(grep "$today" "$LOG_DIR/user_actions.log" | wc -l)
        echo "  📱 Действий пользователей: $actions"
    fi
    
    if [[ -f "$LOG_DIR/participant_changes.log" ]]; then
        adds=$(grep "$today" "$LOG_DIR/participant_changes.log" | grep '"operation": "add"' | wc -l)
        updates=$(grep "$today" "$LOG_DIR/participant_changes.log" | grep '"operation": "update"' | wc -l)
        echo "  ➕ Участников добавлено: $adds"
        echo "  ✏️ Участников обновлено: $updates"
    fi
    
    if [[ -f "$LOG_DIR/errors.log" ]]; then
        errors=$(grep "$today" "$LOG_DIR/errors.log" | wc -l)
        echo "  🚨 Ошибок: $errors"
    fi
}

show_errors() {
    echo "🚨 Последние 10 ошибок:"
    if [[ -f "$LOG_DIR/errors.log" ]]; then
        tail -10 "$LOG_DIR/errors.log"
    else
        echo "Файл ошибок не найден"
    fi
}

show_user() {
    if [[ -z "$1" ]]; then
        echo "❌ Укажите ID пользователя: ./monitor.sh user 12345"
        return
    fi
    
    echo "👤 Действия пользователя $1:"
    if [[ -f "$LOG_DIR/user_actions.log" ]]; then
        grep "\"user_id\": $1" "$LOG_DIR/user_actions.log" | jq -r '
            "\(.timestamp // \"unknown\") | \(.action) | \(.details | tostring)"
        ' 2>/dev/null || grep "\"user_id\": $1" "$LOG_DIR/user_actions.log"
    else
        echo "Файл действий пользователей не найден"
    fi
}

show_performance() {
    echo "🐌 Самые медленные операции (>1 сек):"
    if [[ -f "$LOG_DIR/performance.log" ]]; then
        cat "$LOG_DIR/performance.log" | jq -r 'select(.duration > 1.0) | 
            "\(.duration)s | \(.operation) | 👤\(.user_id) | ID:\(.participant_id // \"N/A\")"
        ' | sort -nr | head -10 2>/dev/null || echo "jq не установлен или файл пуст"
    else
        echo "Файл производительности не найден"
    fi
}

create_report() {
    echo "📈 Создаем HTML отчет..."
    if [[ -f "$LOG_DIR/user_actions.log" ]]; then
        python3 scripts/log_analyzer.py "$LOG_DIR/user_actions.log" --html "logs/report_$(date +%Y%m%d_%H%M%S).html"
        echo "✅ Отчет создан в logs/"
    else
        echo "❌ Файл логов не найден"
    fi
}

# Основная логика
case "$1" in
    "live-users") live_users ;;
    "live-errors") live_errors ;;
    "live-changes") live_changes ;;
    "stats") show_stats ;;
    "errors") show_errors ;;
    "user") show_user "$2" ;;
    "performance") show_performance ;;
    "report") create_report ;;
    *) show_help ;;
esac

