import heapq
from abc import ABC, abstractmethod
from typing import List, Tuple, Iterable, Set, Optional

from .rs_intervalset import MmapIntervalListMapping, MmapIntervalSetMapping

Interval = Tuple[int, int]


def _deoverlap(l: Iterable[Interval], fuzz: int) -> List[Interval]:
    result = []
    for i in l:
        if len(result) == 0:
            result.append(i)
        else:
            x, y = result[-1]
            if min(y, i[1]) + fuzz > max(x, i[0]):
                result[-1] = (min(i[0], x), max(i[1], y))
            else:
                result.append(i)
    return result


class AbstractMmapISetWrapper(ABC):

    @abstractmethod
    def len(self) -> int:
        raise NotImplementedError()

    @abstractmethod
    def get_ids(self) -> List[int]:
        raise NotImplementedError()

    @abstractmethod
    def has_id(self, i: int) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def sum(self):
        raise NotImplementedError()

    @abstractmethod
    def get_intervals(self, i: int, use_default: bool) -> List[Interval]:
        raise NotImplementedError()

    @abstractmethod
    def is_contained(self, i: int, target: int, use_default: bool) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def intersect(
        self, i: int, intervals: List[Interval], use_default: bool
    ) -> List[Interval]:
        raise NotImplementedError()

    def intersect_sum(
        self, i: int, intervals: List[Interval], use_default: bool
    ) -> int:
        return sum(b - a for a, b in self.intersect(i, intervals, use_default))

    def sum(self) -> int:
        return sum(b - a for i in self.get_ids()
                   for a, b in self.get_intervals(i, True))


class MmapIListToISetMapping(AbstractMmapISetWrapper):

    def __init__(self, ilistmap: MmapIntervalListMapping,
                 payload_mask: int, payload_value: int, search_window: int,
                 fuzz: int = 0):
        self._ilistmap = ilistmap
        self._payload_mask = payload_mask
        self._payload_value = payload_value
        self._search_window = search_window
        self._fuzz = fuzz

    def len(self) -> int:
        return self._ilistmap.len()

    def get_ids(self) -> List[int]:
        return self._ilistmap.get_ids()

    def has_id(self, i: int) -> bool:
        return self._ilistmap.has_id(i)

    def get_intervals(self, i: int, use_default: bool) -> List[Interval]:
        return _deoverlap(
            self._ilistmap.get_intervals(
                i, self._payload_mask, self._payload_value, use_default),
            self._fuzz)

    def sum(self) -> int:
        total = 0
        for i in self._ilistmap.get_ids():
            for a, b in _deoverlap(
                self._ilistmap.get_intervals(i, 0, 0, False), self._fuzz
            ):
                total += max(0, b - a)
        return total

    def is_contained(self, i: int, target: int, use_default: bool) -> bool:
        return self._ilistmap.is_contained(
            i, target, self._payload_mask, self._payload_value, use_default,
            self._search_window)

    def intersect(self, i: int, intervals: List[Interval],
                  use_default: bool) -> List[Interval]:
        return _deoverlap(
            self._ilistmap.intersect(
                i, intervals, self._payload_mask, self._payload_value,
                use_default),
            self._fuzz)


class MmapUnionIlistsToISetMapping(AbstractMmapISetWrapper):

    def __init__(self, ilistmaps: List[MmapIntervalListMapping],
                 payload_mask: int, payload_value: int, search_window: int,
                 fuzz: int = 0):
        self._ilistmaps = ilistmaps
        self._payload_mask = payload_mask
        self._payload_value = payload_value
        self._search_window = search_window
        self._fuzz = fuzz

        self.__ids: Optional[List[int]] = None

    @property
    def _ids(self) -> List[int]:
        if self.__ids is None:
            ids = set()
            for ilistmap in self._ilistmaps:
                ids.update(ilistmap.get_ids())
            self.__ids = list(sorted(ids))
        return self.__ids

    def len(self) -> int:
        return len(self._ids)

    def get_ids(self) -> List[int]:
        return self._ids

    def has_id(self, i: int) -> bool:
        return any(ilistmap.has_id(i) for ilistmap in self._ilistmaps)

    def get_intervals(self, i: int, use_default: bool) -> List[Interval]:
        results = []
        for ilistmap in self._ilistmaps:
            intervals = ilistmap.get_intervals(
                i, self._payload_mask, self._payload_value, use_default)
            if intervals:
                results.append(intervals)
        return _deoverlap(heapq.merge(*results), self._fuzz)

    def is_contained(self, i: int, target: int, use_default: bool) -> bool:
        for ilistmap in self._ilistmaps:
            if ilistmap.is_contained(
                i, target, self._payload_mask, self._payload_value,
                use_default, self._search_window
            ):
                return True
        return False

    def intersect(self, i: int, intervals: List[Interval],
                  use_default: bool) -> List[Interval]:
        results = []
        for ilistmap in self._ilistmaps:
            if ilistmap.has_id(i):
                results.append(
                    ilistmap.intersect(
                        i, intervals, self._payload_mask, self._payload_value,
                        use_default))
        return _deoverlap(heapq.merge(*results), self._fuzz)


class MmapISetSubsetMapping(AbstractMmapISetWrapper):

    def __init__(self, isetmap: MmapIntervalSetMapping, subset_ids: Set[int]):
        self._isetmap = isetmap
        self._subset_ids = subset_ids
        self.__ids: Optional[List[int]] = None

    @property
    def _ids(self) -> List[int]:
        if self.__ids is None:
            ids = self._subset_ids.intersection(self._isetmap.get_ids())
            self.__ids = list(sorted(ids))
        return self.__ids

    def len(self) -> int:
        return len(self._ids)

    def get_ids(self) -> List[int]:
        return self._ids

    def has_id(self, i: int) -> bool:
        return i in self._subset_ids and i in self._isetmap.has_id(i)

    def get_intervals(self, i: int, use_default: bool) -> List[Interval]:
        if i in self._subset_ids:
            return self._isetmap.get_intervals(i, use_default)
        elif use_default:
            return []
        else:
            raise IndexError('id not found')

    def is_contained(self, i: int, target: int, use_default: bool) -> bool:
        if i in self._subset_ids:
            return self._isetmap.is_contained(i, target, use_default)
        elif use_default:
            return False
        else:
            raise IndexError('id not found')

    def intersect(self, i: int, intervals: List[Interval],
                  use_default: bool) -> List[Interval]:
        if i in self._subset_ids:
            return self._isetmap.intersect(i, intervals, use_default)
        elif use_default:
            return []
        else:
            raise IndexError('id not found')

    def intersect_sum(
        self, i: int, intervals: List[Interval], use_default: bool
    ) -> int:
        if i in self._subset_ids:
            return self._isetmap.intersect_sum(i, intervals, use_default)
        elif use_default:
            return 0
        else:
            raise IndexError('id not found')


class MmapISetIntersectionMapping(AbstractMmapISetWrapper):

    def __init__(self, isetmaps: List[MmapIntervalSetMapping]):
        self._isetmaps = isetmaps
        self.__ids: Optional[List[int]] = None

    @property
    def _ids(self) -> List[int]:
        if self.__ids is None:
            ids = None
            for isetmap in self._isetmaps:
                if ids is None:
                    ids = set(isetmap.get_ids())
                else:
                    ids.intersection_update(isetmap.get_ids())
            self.__ids = list(sorted(ids))
        return self.__ids

    def len(self) -> int:
        return len(self._ids)

    def get_ids(self) -> List[int]:
        return self._ids

    def has_id(self, i: int) -> bool:
        return all(isetmap.has_id(i) for isetmap in self._isetmaps)

    def get_intervals(self, i: int, use_default: bool) -> List[Interval]:
        if i in self._ids:
            intervals = None
            for isetmap in self._isetmaps:
                if intervals is None:
                    intervals = isetmap.get_intervals(i, use_default)
                else:
                    intervals = isetmap.intersect(i, intervals, use_default)
            return intervals
        elif use_default:
            return []
        else:
            raise IndexError('id not found')

    def is_contained(self, i: int, target: int, use_default: bool) -> bool:
        return all(isetmap.is_contained(i, target, use_default)
                   for isetmap in self._isetmaps)

    def intersect(self, i: int, intervals: List[Interval],
                  use_default: bool) -> List[Interval]:
        if i in self._ids:
            for isetmap in self._isetmaps:
                intervals = isetmap.intersect(i, intervals, use_default)
                if len(intervals) == 0:
                    break
            return intervals
        elif use_default:
            return []
        else:
            raise IndexError('id not found')

    def intersect_sum(self, i: int, intervals: List[Interval],
                      use_default: bool) -> int:
        if i in self._ids:
            result = 0
            for j, isetmap in enumerate(self._isetmaps):
                if j == len(self._isetmaps) - 1:
                    result = isetmap.intersect_sum(i, intervals, use_default)
                else:
                    intervals = isetmap.intersect(i, intervals, use_default)
                    if len(intervals) == 0:
                        break
            return result
        elif use_default:
            return 0
        else:
            raise IndexError('id not found')
