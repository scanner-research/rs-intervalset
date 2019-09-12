from typing import List, Tuple

from .rs_intervalset import MmapIntervalListMapping

Interval = Tuple[int, int]


def _deoverlap(l: List[Interval], fuzz: int) -> List[Interval]:
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


class MmapIListToISetMapping(object):

    def __init__(self, ilistmap: MmapIntervalListMapping,
                 payload_mask: int, payload_value: int, search_window: int,
                 fuzz: int = 0):
        self._ilistmap = ilistmap
        self._payload_mask = payload_mask
        self._payload_value = payload_value
        self._search_window = search_window
        self._fuzz = fuzz

    def get_intervals(self, i: int, use_default: bool) -> List[Interval]:
        return _deoverlap(
            self._ilistmap.get_intervals(
                i, self._payload_mask, self._payload_value, use_default),
            self._fuzz)

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


class MmapUnionIlistsToISetMapping(object):

    def __init__(self, ilistmaps: List[MmapIntervalListMapping],
                 payload_mask: int, payload_value: int, search_window: int,
                 fuzz: int = 0):
        self._ilistmaps = ilistmaps
        self._payload_mask = payload_mask
        self._payload_value = payload_value
        self._search_window = search_window
        self._fuzz = fuzz

    def get_intervals(self, i: int, use_default: bool) -> List[Interval]:
        result: List[Interval] = []
        for ilistmap in self._ilistmaps:
            result.extend(ilistmap.get_intervals(
                i, self._payload_mask, self._payload_value, use_default))
        result.sort()
        return _deoverlap(result, self._fuzz)

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
        result: List[Interval] = []
        for ilistmap in self._ilistmaps:
            if ilistmap.has_id(i):
                result.extend(ilistmap.intersect(
                    i, intervals, self._payload_mask, self._payload_value,
                    use_default))
        result.sort()
        return _deoverlap(result, self._fuzz)
