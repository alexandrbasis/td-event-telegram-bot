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
    from constants import DEPARTMENT_KEYWORDS, ISRAEL_CITIES

    cache.set("departments", DEPARTMENT_KEYWORDS)
    cache.set("cities", ISRAEL_CITIES)

