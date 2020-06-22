# rs-intervalset

Python module for fast indexing of immutable memory-mapped intervalsets.

## Install

First, make sure Rust is installed. Rust nightly build is required for pyo3.
Run `rustup override set nightly-2020-06-01` inside the directory where the
repository is cloned (tested with nightly 1.45.0).
Next, run `python3 setup.py install --user`.

## Tests

Run `pytest -v .` from inside the `tests` directory.

## Types

The implementations for the following types are located in `/src` and file
writers are available in `rs_intervalset/writer.py`.

### MmapIntervalSetMapping

Intervals are grouped by video id. For a single video id:
 - u32 (LE) ID
 - u32 (LE) Number of intervals
 - For each interval (sorted by start):
    - u32 (LE) start
    - u32 (LE) end

Repeat for each video id.

For indexing functionality to be correct, intervals must be non-overlapping and
sorted.

### MmapIntervalListMapping

Intervals are grouped by video id. For a single video id:
 - u32 (LE) ID
 - u32 (LE) Number of intervals
 - For each interval (sorted by start):
    - u32 (LE) start
    - u32 (LE) end
    - up to 8 bytes (LE) payload

Repeat for each video id.

Intervals must be sorted by start time, but can overlap.
