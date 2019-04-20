# rs-imntervalset

Python module for operations on mmapped intervals.

## Install

First, make sure Rust is installed. Run `rustup override set nightly` inside the directory where the repository is cloned. Next, run `python3 setup.py install --user`.

## Tests

Run `pytest -v tests`.

## Data format

Intervals are grouped by video id. For a single video id:
 - u32 (LE) ID
 - u32 (LE) Number of intervals
 - For each interval (sorted by start):
    - u32 (LE) start
    - u32 (LE) end

Repeat for each video id.

For indexing functionality to be correct, intervals must be non-overlapping and
sorted.
