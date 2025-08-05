from constants import (
    GENDER_DISPLAY,
    ROLE_DISPLAY,
    SIZE_DISPLAY,
    DEPARTMENT_DISPLAY,
)


class MessageFormatter:
    @staticmethod
    def format_participant_info(participant_data: dict) -> str:
        gender_key = participant_data.get("Gender") or ""
        size_key = participant_data.get("Size") or ""
        role_key = participant_data.get("Role") or ""
        dept_key = participant_data.get("Department") or ""

        gender = GENDER_DISPLAY.get(gender_key, "Не указано")
        size = SIZE_DISPLAY.get(size_key, "Не указано")
        role = ROLE_DISPLAY.get(role_key, role_key)
        department = DEPARTMENT_DISPLAY.get(dept_key, dept_key or "Не указано")

        text = (
            f"Имя (рус): {participant_data.get('FullNameRU') or 'Не указано'}\n"
            f"Имя (англ): {participant_data.get('FullNameEN') or 'Не указано'}\n"
            f"Пол: {gender}\n"
            f"Размер: {size}\n"
            f"Церковь: {participant_data.get('Church') or 'Не указано'}\n"
            f"Роль: {role}"
        )

        if role_key == "TEAM":
            text += f"\nДепартамент: {department}"

        text += (
            f"\nГород: {participant_data.get('CountryAndCity') or 'Не указано'}\n"
            f"Кто подал: {participant_data.get('SubmittedBy') or 'Не указано'}\n"
            f"Контакты: {participant_data.get('ContactInformation') or 'Не указано'}"
        )
        return text
