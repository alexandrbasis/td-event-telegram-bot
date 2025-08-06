class SimpleCache:
    def __init__(self):
        self._cache = {}

    def get(self, key):
        return self._cache.get(key)

    def set(self, key, value):
        self._cache[key] = value

    def clear(self):
        self._cache.clear()


cache = SimpleCache()


def load_reference_data():
    """Load cities and departments into cache."""
    from src.constants import ISRAEL_CITIES
    from src.utils.field_normalizer import field_normalizer

    # Теперь департаменты берем из нормализатора
    cache.set("departments", field_normalizer.DEPARTMENT_MAPPINGS)
    cache.set("cities", ISRAEL_CITIES)
    cache.set("churches", [])  # Можно добавить известные церкви
