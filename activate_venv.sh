#!/bin/bash

# Скрипт для активации виртуальной среды TD Bot
# ВАЖНО: Запускайте через 'source ./activate_venv.sh' или '. ./activate_venv.sh'

echo "🤖 Активация виртуальной среды TD Bot..."

# Проверяем, что скрипт запущен через source, иначе активация не сохранится
is_sourced=false
# bash
if [ -n "$BASH_VERSION" ]; then
  if [ "${BASH_SOURCE[0]}" != "$0" ]; then
    is_sourced=true
  fi
fi
# zsh
if [ -n "$ZSH_VERSION" ]; then
  case $ZSH_EVAL_CONTEXT in
    *:file) is_sourced=true;;
  esac
fi

if [ "$is_sourced" != true ]; then
  echo ""
  echo "❌ ОШИБКА: Скрипт запущен неправильно!"
  echo ""
  echo "🔧 Правильный способ запуска:"
  echo "   source ./activate_venv.sh"
  echo "   или"
  echo "   . ./activate_venv.sh"
  echo ""
  echo "⚠️  Если запустить через './activate_venv.sh', виртуальная среда"
  echo "   не активируется в текущей сессии терминала."
  echo ""
  return 2 2>/dev/null || exit 2
fi

# Проверяем, что мы в правильной директории
if [ ! -d "venv" ]; then
    echo "❌ Ошибка: папка venv не найдена. Убедитесь, что вы находитесь в корне проекта."
    exit 1
fi

# Для zsh включаем форматирование промпта (если выключено)
if [ -n "$ZSH_VERSION" ]; then
    setopt PROMPT_PERCENT 2>/dev/null || true
    setopt PROMPT_SUBST 2>/dev/null || true
fi

# Кастомный префикс имени виртуальной среды в промпте
export VIRTUAL_ENV_PROMPT="(TD Bot) "

# Исправляем промпт для zsh если он сломан
if [ -n "$ZSH_VERSION" ] && [[ "$PS1" == *"%n@%m"* ]]; then
    # Если промпт показывает сырые переменные, устанавливаем простой рабочий промпт
    export PS1="(TD Bot) %~ $ "
fi

# Убираем алиас python если он есть
unalias python 2>/dev/null || true

# Активируем виртуальную среду
source venv/bin/activate

# Проверяем активацию
if [ "$VIRTUAL_ENV" != "" ]; then
    echo "✅ Виртуальная среда активирована: $VIRTUAL_ENV"
    echo "🐍 Python версия: $(python --version)"
    echo "📦 Установленные пакеты:"
    pip list | grep -E "(python-telegram-bot|pyairtable|python-dotenv)" | sed 's/^/   /'
    echo ""
    echo "🚀 Готово! Теперь можно запускать бота командой: python main.py"
else
    echo "❌ Ошибка: виртуальная среда не активирована"
    exit 1
fi
