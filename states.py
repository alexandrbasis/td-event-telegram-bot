# states.py
# Определяем состояния для ConversationHandler
# Числа выбраны произвольно, главное, чтобы они были уникальны
GETTING_DATA, CONFIRMING_DATA, CONFIRMING_DUPLICATE, COLLECTING_DATA = range(4)

# Состояние для пошагового заполнения недостающих полей
FILLING_MISSING_FIELDS = 5

# Состояние восстановления после технических ошибок
RECOVERING = 6

# Состояния для поиска участников
SEARCHING_PARTICIPANTS = 7
SELECTING_PARTICIPANT = 8
CHOOSING_ACTION = 9
EXECUTING_ACTION = 10

# Состояния для внесения оплаты
ENTERING_PAYMENT_AMOUNT = 11
CONFIRMING_PAYMENT = 12
