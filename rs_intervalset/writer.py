from typing import List, Tuple


class IntervalSetMappingWriter(object):

    def __init__(self, path: str):
        self._fp = open(path, 'wb')
        self._path = path

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def __fmt_u32(self, v):
        return v.to_bytes(4, byteorder='little')

    def write(self, id_: int, intervals: List[Tuple[int, int]]):
        self._fp.write(self.__fmt_u32(id_))
        self._fp.write(self.__fmt_u32(len(intervals)))
        for a, b in intervals:
            assert b > a, 'invalid interval: ({}, {})'.format(a, b)
            self._fp.write(self.__fmt_u32(a))
            self._fp.write(self.__fmt_u32(b))

    def close(self):
        if self._fp is not None:
            self._fp.close()
            self._fp = None

    @property
    def path(self):
        return self._path
