"""Helper for exposing a queryset across a domain boundary as read-only DTOs."""


class MappedQuery:
    """Lazy, sliceable, countable view of a queryset whose rows are mapped to DTOs.

    Slicing hits the database with LIMIT/OFFSET before mapping and `count()` runs SQL COUNT, so DRF/Django
    pagination works on it without loading every row. Callers never see model instances.
    """

    def __init__(self, queryset, mapper):
        self._qs = queryset
        self._mapper = mapper

    @property
    def ordered(self):
        return getattr(self._qs, "ordered", True)

    def count(self) -> int:
        return self._qs.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, key):
        if isinstance(key, slice):
            return [self._mapper(row) for row in self._qs[key]]
        return self._mapper(self._qs[key])

    def __iter__(self):
        return (self._mapper(row) for row in self._qs)
