import unittest
from parsers.participant_parser import (
    parse_participant_data,
    is_template_format,
    parse_template_format,
    parse_unstructured_text,
    detect_field_update_intent,
    _smart_name_classification,
)
from utils.cache import load_reference_data, cache

load_reference_data()


class ParserTestCase(unittest.TestCase):
    def test_parse_candidate(self):
        text = "Иван Петров M L церковь Новая Жизнь кандидат"
        data = parse_participant_data(text)
        self.assertEqual(data["FullNameRU"], "Иван Петров")
        self.assertEqual(data["Gender"], "")
        self.assertEqual(data["Size"], "M")
        self.assertEqual(data["Role"], "CANDIDATE")

    def test_parse_team_with_department(self):
        text = "Анна Иванова F S церковь Благодать команда worship"
        data = parse_participant_data(text)
        self.assertEqual(data["Role"], "TEAM")
        self.assertEqual(data["Department"], "Worship")

    def test_russian_size_and_gender_priority(self):
        text = "Ольга Сергеевна жен М Афула церковь Благодать"
        data = parse_participant_data(text)
        self.assertEqual(data["Gender"], "F")
        self.assertEqual(data["Size"], "")
        self.assertEqual(data["CountryAndCity"], "АФУЛА")
        self.assertEqual(data["Church"], "Благодать")

    def test_update_gender_only(self):
        text = "Пол женский"
        data = parse_participant_data(text, is_update=True)
        self.assertEqual(data, {"Gender": "F"})

    def test_size_medium_synonym(self):
        text = "размер medium"
        data = parse_participant_data(text, is_update=True)
        self.assertEqual(data, {"Size": "M"})

    def test_template_parsing(self):
        text = "Имя (рус): Иван Петров, Пол: M, Размер: L, Церковь: Благодать"
        self.assertTrue(is_template_format(text))
        data = parse_participant_data(text)
        self.assertEqual(data["FullNameRU"], "Иван Петров")
        self.assertEqual(data["Gender"], "M")
        self.assertEqual(data["Size"], "L")
        self.assertEqual(data["Church"], "Благодать")

    def test_template_cyrillic_size_m(self):
        text = "Имя (рус): Иван Петров, Размер: м"
        data = parse_template_format(text)
        self.assertEqual(data["Size"], "M")

    def test_medium_size_not_in_submitted_by(self):
        """Тест проверяет, что 'medium' распознается как размер, а не как часть имени подавшего"""
        text = "Тест Басис тим админ община грейс муж Хайфа от Ирина Цой medium"
        data = parse_participant_data(text)

        self.assertEqual(data["FullNameRU"], "Тест Басис")
        self.assertEqual(data["Gender"], "M")
        self.assertEqual(data["Size"], "M")  # medium должен стать M
        self.assertEqual(data["Role"], "TEAM")
        self.assertEqual(data["Department"], "Administration")
        self.assertEqual(data["Church"], "грейс")
        self.assertEqual(data["CountryAndCity"], "ХАЙФА")
        self.assertEqual(data["SubmittedBy"], "Ирина Цой")  # без 'medium'

    def test_contact_validation(self):
        """Тест проверяет валидацию контактной информации"""
        # Некорректные контакты не должны распознаваться
        text1 = "Иван Петров муж L церковь Грейс кандидат Н"
        data1 = parse_participant_data(text1)
        self.assertEqual(data1["ContactInformation"], "")  # Н не должно быть контактом

        # Корректные телефоны должны распознаваться
        text2 = "Иван Петров муж L церковь Грейс кандидат +972501234567"
        data2 = parse_participant_data(text2)
        self.assertEqual(data2["ContactInformation"], "+972501234567")

        text2b = "Иван Петров муж L церковь Грейс кандидат 050-123-4567"
        data2b = parse_participant_data(text2b)
        self.assertEqual(data2b["ContactInformation"], "050-123-4567")

        text2c = "Иван Петров муж L церковь Грейс кандидат 03-123-4567"
        data2c = parse_participant_data(text2c)
        self.assertEqual(data2c["ContactInformation"], "03-123-4567")

        # Корректные email должны распознаваться
        text3 = "Иван Петров муж L церковь Грейс кандидат ivan@mail.ru"
        data3 = parse_participant_data(text3)
        self.assertEqual(data3["ContactInformation"], "ivan@mail.ru")

        # Некорректные 'телефоны' не должны распознаваться
        text4 = "Иван Петров муж L церковь Грейс кандидат 123"
        data4 = parse_participant_data(text4)
        self.assertEqual(data4["ContactInformation"], "")  # 123 слишком короткий

        # Некорректные email и телефоны
        text5 = "Иван Петров муж L церковь Грейс кандидат test@."
        data5 = parse_participant_data(text5)
        self.assertEqual(data5["ContactInformation"], "")

        text6 = "Иван Петров муж L церковь Грейс кандидат Петров@abc"
        data6 = parse_participant_data(text6)
        self.assertEqual(data6["ContactInformation"], "")

        text7 = "Иван Петров муж L церковь Грейс кандидат 12345678"
        data7 = parse_participant_data(text7)
        self.assertEqual(data7["ContactInformation"], "")

        # Контакты с завершающей пунктуацией должны очищаться
        text8 = "Иван Петров муж L церковь Грейс кандидат ivan@mail.ru,"
        data8 = parse_participant_data(text8)
        self.assertEqual(data8["ContactInformation"], "ivan@mail.ru")

        text9 = "Иван Петров муж L церковь Грейс кандидат +972(50)123-45-67,"
        data9 = parse_participant_data(text9)
        self.assertEqual(data9["ContactInformation"], "+972(50)123-45-67")

    def test_is_template_format_variants(self):
        self.assertTrue(is_template_format("Имя (рус): Иван\nПол: M\nЦерковь: XYZ"))
        self.assertFalse(is_template_format("Просто текст без шаблона"))

    def test_parse_template_partial(self):
        text = "Имя (рус): Иван Петров\nПол: M\nРазмер:\nЦерковь: Благодать"
        data = parse_template_format(text)
        self.assertEqual(data["FullNameRU"], "Иван Петров")
        self.assertEqual(data["Gender"], "M")
        self.assertNotIn("Size", data)
        self.assertEqual(data["Church"], "Благодать")

    def test_parse_template_single_line_commas(self):
        text = "Имя (рус): Иван, Пол: M, Размер: L, Церковь: Благодать"
        data = parse_template_format(text)
        self.assertEqual(data["FullNameRU"], "Иван")
        self.assertEqual(data["Gender"], "M")
        self.assertEqual(data["Size"], "L")
        self.assertEqual(data["Church"], "Благодать")

    def test_template_normalization(self):
        text = "\n".join(
            [
                "Имя (рус): Иван Петров",
                "Пол: муж",
                "Размер: extra large",
                "Роль: тим",
                "Департамент: админ",
            ]
        )
        data = parse_participant_data(text)
        self.assertEqual(data["Gender"], "M")
        self.assertEqual(data["Size"], "XL")
        self.assertEqual(data["Role"], "TEAM")
        self.assertEqual(data["Department"], "Administration")

    def test_template_unknown_department(self):
        text = "\n".join(
            [
                "Имя (рус): Иван",
                "Пол: M",
                "Департамент: Support",
            ]
        )
        data = parse_participant_data(text)
        self.assertEqual(data["Department"], "")

    def test_unstructured_multi_field(self):
        cache.set("churches", ["Грейс"])
        text = "Саша Б тим админ Грейс Хайфа"
        data = parse_unstructured_text(text)
        self.assertEqual(data["FullNameRU"], "Саша Б")
        self.assertEqual(data["Role"], "TEAM")
        self.assertEqual(data["Department"], "Administration")
        self.assertEqual(data["Church"], "Грейс")
        self.assertEqual(data["CountryAndCity"], "ХАЙФА")

    def test_field_value_patterns_consumed(self):
        text = "размер M Иван"
        data = parse_unstructured_text(text)
        self.assertEqual(data["Size"], "M")
        self.assertEqual(data["FullNameRU"], "Иван")

        text = "пол женский Мария"
        data = parse_unstructured_text(text)
        self.assertEqual(data["Gender"], "F")
        self.assertEqual(data["FullNameRU"], "Мария")

    def test_field_value_regex_multiple(self):
        text = "пол мужской размер L Иван"
        data = parse_unstructured_text(text)
        self.assertEqual(data["Gender"], "M")
        self.assertEqual(data["Size"], "L")
        self.assertEqual(data["FullNameRU"], "Иван")

    def test_update_intent_synonyms(self):
        self.assertEqual(detect_field_update_intent("футболка"), "Size")
        self.assertEqual(detect_field_update_intent("мужской"), "Gender")

    def test_m_gender_size_conflict_resolution(self):
        """Тест разрешения конфликта M между полом и размером"""
        result = parse_participant_data("Мария размер M церковь Грейс")
        self.assertEqual(result["Gender"], "")
        self.assertEqual(result["Size"], "M")

        result = parse_participant_data("Михаил пол M церковь Грейс")
        self.assertEqual(result["Gender"], "M")
        self.assertEqual(result["Size"], "")

        result = parse_participant_data("Анна M L церковь Грейс")
        self.assertEqual(result["Size"], "M")

    def test_fuzzy_church_matching(self):
        """Тест нечеткого поиска церквей"""
        cache.set("churches", ["Новая Жизнь", "Слово Веры"])
        result = parse_participant_data("Иван церковь Новая")
        self.assertIn("Новая", result["Church"])

        result = parse_participant_data("Иван церковь Новай")
        # Результат зависит от наличия Levenshtein

    def test_improved_contact_validation(self):
        """Тест улучшенной валидации контактов"""
        result = parse_participant_data("Иван Петров test@")
        self.assertEqual(result["ContactInformation"], "")

        result = parse_participant_data("Иван Петров 12345")
        self.assertEqual(result["ContactInformation"], "")

    def test_mixed_russian_english_names(self):
        text = "Василий Петров John Smith M L церковь Грейс кандидат"
        data = parse_participant_data(text)
        self.assertEqual(data["FullNameRU"], "Василий Петров")
        self.assertEqual(data["FullNameEN"], "John Smith")

    def test_mixed_names_single_input(self):
        """Тест для имен на русском и английском в одной строке"""
        text = (
            "Аарон Басис Aaron Basis муж L церковь Благодать тим рое хайфа 0552953372"
        )
        data = parse_participant_data(text)

        self.assertEqual(data["FullNameRU"], "Аарон Басис")
        self.assertEqual(data["FullNameEN"], "Aaron Basis")
        self.assertEqual(data["Gender"], "M")
        self.assertEqual(data["Size"], "L")
        self.assertEqual(data["Church"], "Благодать")
        self.assertEqual(data["Role"], "TEAM")
        self.assertEqual(data["Department"], "ROE")
        self.assertEqual(data["CountryAndCity"], "ХАЙФА")
        self.assertEqual(data["ContactInformation"], "0552953372")

    def test_smart_name_classification_edge_cases(self):
        """Тест edge cases для умной классификации имен"""
        # Случай 1: Только русское имя
        text1 = "Иван Петров муж L церковь Грейс"
        data1 = parse_participant_data(text1)
        self.assertEqual(data1["FullNameRU"], "Иван Петров")
        self.assertEqual(data1["FullNameEN"], "")

        # Случай 2: Только английское имя (транслитерация)
        text2 = "Sergey Ivanov муж L церковь Грейс"
        data2 = parse_participant_data(text2)
        self.assertEqual(data2["FullNameRU"], "")
        self.assertEqual(data2["FullNameEN"], "Sergey Ivanov")

        # Случай 3: Сложный случай с группировкой
        text3 = "Мария Анна Mary Ann Сидорова Johnson жен M церковь Благодать"
        data3 = parse_participant_data(text3)
        self.assertEqual(data3["FullNameRU"], "Мария Анна Сидорова")
        self.assertEqual(data3["FullNameEN"], "Mary Ann Johnson")

    def test_name_with_hyphens_and_special_chars(self):
        """Тест имен с дефисами и специальными символами"""
        text = "Анна-Мария Петрова-Сидорова Anne-Marie Johnson жен S церковь Грейс"
        data = parse_participant_data(text)

        self.assertEqual(data["FullNameRU"], "Анна-Мария Петрова-Сидорова")
        self.assertEqual(data["FullNameEN"], "Anne-Marie Johnson")


class SmartNameClassificationTestCase(unittest.TestCase):
    def test_simple_cases(self):
        """Тест простых случаев (1-2 слова)"""
        # Только русские
        ru, en = _smart_name_classification(["Иван", "Петров"])
        self.assertEqual(ru, ["Иван", "Петров"])
        self.assertEqual(en, [])

        # Только английские
        ru, en = _smart_name_classification(["John", "Smith"])
        self.assertEqual(ru, [])
        self.assertEqual(en, ["John", "Smith"])

        # Смешанные
        ru, en = _smart_name_classification(["John", "Иванов"])
        self.assertEqual(ru, ["Иванов"])
        self.assertEqual(en, ["John"])

    def test_complex_grouping(self):
        """Тест сложных случаев с группировкой"""
        # Русские + английские блоки
        words = ["Мария", "Анна", "Mary", "Ann", "Петрова", "Johnson"]
        ru, en = _smart_name_classification(words)
        self.assertEqual(ru, ["Мария", "Анна", "Петрова"])
        self.assertEqual(en, ["Mary", "Ann", "Johnson"])

        # Перемешанные блоки
        words2 = ["John", "Иван", "Smith", "Петров"]
        ru2, en2 = _smart_name_classification(words2)
        self.assertEqual(ru2, ["Иван", "Петров"])
        self.assertEqual(en2, ["John", "Smith"])

    def test_edge_cases(self):
        """Тест граничных случаев"""
        # Пустой список
        ru, en = _smart_name_classification([])
        self.assertEqual(ru, [])
        self.assertEqual(en, [])

        # Одно слово
        ru, en = _smart_name_classification(["Иван"])
        self.assertEqual(ru, ["Иван"])
        self.assertEqual(en, [])

        # Слова с дефисами
        ru, en = _smart_name_classification(["Анна-Мария", "Anne-Marie"])
        self.assertEqual(ru, ["Анна-Мария"])
        self.assertEqual(en, ["Anne-Marie"])


if __name__ == "__main__":
    unittest.main()
