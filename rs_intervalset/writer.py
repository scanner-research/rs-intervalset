from typing import List, Tuple, Optional, BinaryIO


class IntervalSetMappingWriter(object):

    def __init__(self, path: str, append: bool = False):
        mode = 'ab' if append else 'wb'
        self._fp: Optional[BinaryIO] = open(path, mode)
        self._path = path

    def __enter__(self) -> 'IntervalSetMappingWriter':
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def __fmt_u32(self, v: int) -> bytes:
        return v.to_bytes(4, byteorder='little')

    def write(self, id_: int, intervals: List[Tuple[int, int]]) -> None:
        assert self._fp is not None
        self._fp.write(self.__fmt_u32(id_))
        self._fp.write(self.__fmt_u32(len(intervals)))
        for a, b in intervals:
            assert b > a, 'invalid interval: ({}, {})'.format(a, b)
            self._fp.write(self.__fmt_u32(a))
            self._fp.write(self.__fmt_u32(b))

    def close(self) -> None:
        if self._fp is not None:
            self._fp.close()
            self._fp = None


class IntervalListMappingWriter(object):

    def __init__(self, path: str, payload_len: int, append: bool = False):
        mode = 'ab' if append else 'wb'
        self._fp: Optional[BinaryIO] = open(path, mode)
        self._path = path
        self._payload_len = payload_len

    def __enter__(self) -> 'IntervalListMappingWriter':
        return self

    def __exit__(self, type, value, tb) -> None:
        self.close()

    def __fmt_u32(self, v: int) -> bytes:
        return v.to_bytes(4, byteorder='little')

    def __fmt_payload(self, v: int) -> bytes:
        return v.to_bytes(self._payload_len, byteorder='little')

    def write(self, id_: int, intervals: List[Tuple[int, int, int]]) -> None:
        assert self._fp is not None
        self._fp.write(self.__fmt_u32(id_))
        self._fp.write(self.__fmt_u32(len(intervals)))
        for a, b, c in intervals:
            assert b > a, 'invalid interval: ({}, {})'.format(a, b)
            self._fp.write(self.__fmt_u32(a))
            self._fp.write(self.__fmt_u32(b))
            self._fp.write(self.__fmt_payload(c))

    def close(self) -> None:
        if self._fp is not None:
            self._fp.close()
            self._fp = None
