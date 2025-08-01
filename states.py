# states.py
# Определяем состояния для ConversationHandler
# Числа выбраны произвольно, главное, чтобы они были уникальны
GETTING_DATA, CONFIRMING_DATA, CONFIRMING_DUPLICATE, COLLECTING_DATA = range(4)

# Состояние для пошагового заполнения недостающих полей
FILLING_MISSING_FIELDS = 5

# Состояние восстановления после технических ошибок
RECOVERING = 6
