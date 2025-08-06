from typing import Iterable, List, TypeVar

T = TypeVar("T")


def paginate(items: Iterable[T], page: int, per_page: int) -> List[T]:
    start = (page - 1) * per_page
    end = start + per_page
    return list(items)[start:end]
