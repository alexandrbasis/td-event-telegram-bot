# states.py
# Определяем состояния для ConversationHandler
# Числа выбраны произвольно, главное, чтобы они были уникальны
GETTING_DATA, CONFIRMING_DATA, CONFIRMING_DUPLICATE, COLLECTING_DATA = range(4)
