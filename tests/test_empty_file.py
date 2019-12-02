import os
import pytest

from rs_intervalset import MmapIntervalSetMapping, MmapIntervalListMapping


CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(CURRENT_DIR, '.empty.bin')


@pytest.fixture(scope='session', autouse=True)
def dummy_data():
    with open(DATA_PATH, 'w') as _:
        pass
    yield
    os.remove(DATA_PATH)


def test_empty_isetmap():
    isetmap = MmapIntervalSetMapping(DATA_PATH)
    assert isetmap.sum() == 0


def test_empty_ilistmap():
    ilistmap = MmapIntervalListMapping(DATA_PATH, 0)
    assert ilistmap.sum(0, 0) == 0
