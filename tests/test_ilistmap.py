import os
import pickle
import pytest
import random

from rs_intervalset import MmapIntervalListMapping
from rs_intervalset.writer import IntervalListMappingWriter

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(CURRENT_DIR, '.ilistmap.test_data.bin')
TRUTH_PATH = os.path.join(CURRENT_DIR, '.ilistmap.test_truth.bin')

PAYLOAD_LEN = 1
DISTINCT_PAYLOADS = 20
N = 1000
M = 1000
MAX_T = 100000
MAX_SPAN = 5000
N_REPEAT = 10


@pytest.fixture(scope='session', autouse=True)
def dummy_data():

    with IntervalListMappingWriter(DATA_PATH, PAYLOAD_LEN) as writer:
        ground_truth = {}
        for i in range(N):
            intervals = []
            for j in range(M):
                a = random.randint(0, MAX_T - 1)
                b = min(MAX_T, a + random.randint(1, MAX_SPAN))
                c = random.randint(0, DISTINCT_PAYLOADS - 1)
                intervals.append((a, b, c))
            intervals.sort()
            writer.write(i, intervals)
            ground_truth[i] = intervals
        with open(TRUTH_PATH, 'wb') as truth_fh:
            pickle.dump(ground_truth, truth_fh)
    yield
    os.remove(DATA_PATH)
    os.remove(TRUTH_PATH)


def _load_truth():
    with open(TRUTH_PATH, 'rb') as f:
        return pickle.load(f)


def _filter(l, mask, value):
    return [x for x in l if (x[2] & mask) == value]


def _deoverlap(l):
    ret = []
    for x in l:
        if len(ret) == 0:
            ret.append(x)
        else:
            if min(x[1], ret[-1][1]) > max(x[0], ret[-1][0]):
                ret[-1] = (min(x[0], ret[-1][0]), max(x[1], ret[-1][1]))
            else:
                ret.append(x)
    return ret


def test_integrity():
    truth = _load_truth()
    isetmap = MmapIntervalListMapping(DATA_PATH, PAYLOAD_LEN)
    assert len(truth) == isetmap.len()
    assert set(truth.keys()) == set(isetmap.get_ids())
    for i in truth:
        assert isetmap.has_id(i)
        for j in range(DISTINCT_PAYLOADS):
            assert (len(_filter(truth[i], 0xFF, j))
                    == isetmap.get_interval_count(i, 0xFF, j))


def test_contains():
    truth = _load_truth()
    isetmap = MmapIntervalListMapping(DATA_PATH, PAYLOAD_LEN)

    i = random.choice(list(truth.keys()))

    def truth_contains(v, mask, payload):
        for (a, b, _) in _filter(truth[i], mask, payload):
            if v >= a and v < b:
                return True
        return False

    for v in range(MAX_T):
        j = random.randint(0, DISTINCT_PAYLOADS - 1)
        assert truth_contains(v, 0xFF, j) == \
            isetmap.is_contained(i, v, 0xFF, j, False, MAX_SPAN), \
            'Truth: {}'.format(truth[i])


def test_sum():
    # TODO: add test for summing all intervals
    truth = _load_truth()
    isetmap = MmapIntervalListMapping(DATA_PATH, PAYLOAD_LEN)
    for _ in range(N_REPEAT):
        i = random.choice(list(truth.keys()))
        for j in range(DISTINCT_PAYLOADS):
            assert (
                sum(x[1] - x[0] for x in _filter(truth[i], 0xFF, j))
                == isetmap.intersect_sum(i, [(0, MAX_T)], 0xFF, j, False))


def test_intersect():
    truth = _load_truth()
    isetmap = MmapIntervalListMapping(DATA_PATH, PAYLOAD_LEN)
    for _ in range(N_REPEAT):
        i = random.choice(list(truth.keys()))
        for j in range(DISTINCT_PAYLOADS):
            true_iset = _deoverlap(
                (x[0], x[1]) for x in _filter(truth[i], 0xFF, j)
            )
            assert (
                true_iset
                == isetmap.intersect(i, [(0, MAX_T)], 0xFF, j, False))
