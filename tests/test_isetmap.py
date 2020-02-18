import os
import pickle
import pytest
import random

from rs_intervalset import MmapIntervalSetMapping
from rs_intervalset.writer import IntervalSetMappingWriter


CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(CURRENT_DIR, '.isetmap.test_data.bin')
TRUTH_PATH = os.path.join(CURRENT_DIR, '.isetmap.test_truth.bin')


N = 1000
MAX_SKIP = 1000
MAX_T = 100000
MAX_T_SPAN = 1000
N_REPEAT = 10


@pytest.fixture(scope='session', autouse=True)
def dummy_data():

    with IntervalSetMappingWriter(DATA_PATH) as writer:
        ground_truth = {}
        for i in range(N):
            intervals = []
            max_sampled = 0
            while max_sampled < MAX_T:
                a = random.randint(max_sampled, max_sampled + MAX_SKIP)
                if a >= MAX_T:
                    break
                b = min(MAX_T, a + random.randint(1, MAX_T_SPAN))
                intervals.append((a, b))
                max_sampled = b + 1
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


def test_integrity():
    truth = _load_truth()
    isetmap = MmapIntervalSetMapping(DATA_PATH)
    assert len(truth) == isetmap.len()
    assert set(truth.keys()) == set(isetmap.get_ids())
    for i in truth:
        assert isetmap.has_id(i)
        assert len(truth[i]) == isetmap.get_interval_count(i)
        assert len(truth[i]) == len(isetmap.get_intervals(i, False))
        for j, interval in enumerate(truth[i]):
            assert interval == isetmap.get_interval(i, j)


def _is_close(a: float, b: float, t: float = 1e-6) -> bool:
    return abs(a - b) <= t


def test_sum():
    truth = _load_truth()
    isetmap = MmapIntervalSetMapping(DATA_PATH)
    true_sum = sum(
        sum(b - a for a, b in intervals)
        for intervals in truth.values())
    calc_sum = isetmap.sum()
    assert _is_close(true_sum, calc_sum), \
        'diff: {} -- {}'.format(true_sum, calc_sum)


def test_contains():
    truth = _load_truth()
    isetmap = MmapIntervalSetMapping(DATA_PATH)

    i = random.choice(list(truth.keys()))

    def truth_contains(v):
        for (a, b) in truth[i]:
            if v >= a and v < b:
                return True
        return False

    for v in range(MAX_T):
        assert truth_contains(v) == isetmap.is_contained(i, v, False), \
            'diff: {} -- {}'.format(v, isetmap.get_intervals(i, False))


def test_has_intersection():
    truth = _load_truth()
    isetmap = MmapIntervalSetMapping(DATA_PATH)

    def has_intersection(intervals, a, b):
        for x, y in intervals:
            if min(b, y) - max(a, x) > 0:
                return True
        return False

    for _ in range(N_REPEAT):
        i = random.choice(list(truth.keys()))
        intervals = isetmap.get_intervals(i, False)
        for j in range(MAX_T):
            a = j
            b = j + 1
            assert isetmap.has_intersection(i, a, b, False) == has_intersection(intervals, a, b)


def test_intersect():
    truth = _load_truth()
    isetmap = MmapIntervalSetMapping(DATA_PATH)
    for _ in range(N_REPEAT):
        i = random.choice(list(truth.keys()))
        assert truth[i] == isetmap.intersect(i, [(0, MAX_T)], False)


def test_intersect_sum():
    truth = _load_truth()
    isetmap = MmapIntervalSetMapping(DATA_PATH)

    for _ in range(N_REPEAT):
        i = random.choice(list(truth.keys()))
        true_sum = sum(b - a for a, b in truth[i])
        assert true_sum == isetmap.intersect_sum(i, [(0, MAX_T)], False)


def test_minus():
    truth = _load_truth()
    isetmap = MmapIntervalSetMapping(DATA_PATH)

    def naive_minus(intervals, min_val, max_val):
        result = []
        i = min_val
        for a, b in intervals:
            if a - i > 0:
                result.append((i, a))
            i = b
        if i < max_val:
            result.append((i, max_val))
        return result

    for _ in range(N_REPEAT):
        i = random.choice(list(truth.keys()))
        assert naive_minus(truth[i], 0, MAX_T) == \
            isetmap.minus(i, [(0, MAX_T)], False)
