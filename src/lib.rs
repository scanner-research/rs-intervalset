#![feature(specialization)]

extern crate pyo3;
extern crate memmap;
extern crate byteorder;

use pyo3::prelude::*;
use pyo3::exceptions;
use std::cmp::{max, min};
use std::collections::HashMap;
use std::mem;
use std::fs::File;
use std::io::Cursor;
use byteorder::{ReadBytesExt, LittleEndian};
use memmap::{MmapOptions, Mmap};

pub type Id = u32;
pub type Value = u32;
pub type Interval = (Value, Value);

const INTERVAL_SIZE: usize = 2 * mem::size_of::<u32>();

fn mmap_read_u32(m: &Mmap, i: usize) -> u32 {
    let mut rdr = Cursor::new(&m[i..i + mem::size_of::<u32>()]);
    rdr.read_u32::<LittleEndian>().unwrap()
}

fn parse_offsets(m: &Mmap) -> Option<HashMap<Id, (usize, usize)>> {
    let mut i = 0;
    let mut id_offsets: HashMap<Id, (usize, usize)> = HashMap::new();
    while i < m.len() {
        let id = mmap_read_u32(m, i) as Id;
        let n = mmap_read_u32(m, i + mem::size_of::<Id>()) as usize;
        i += mem::size_of::<Id>() + mem::size_of::<u32>();
        id_offsets.insert(id, (i, n));
        i += n * INTERVAL_SIZE;
    }
    if i != m.len() {
        None
    } else {
        Some(id_offsets)
    }
}

struct _MmapIntervalSetMapping {
    data: Mmap,
    offsets: HashMap<Id, (usize, usize)>,
}

impl _MmapIntervalSetMapping {

    fn read_interval(&self, i: usize) -> Interval {
        (mmap_read_u32(&self.data, i), mmap_read_u32(&self.data, i + mem::size_of::<u32>()))
    }

    fn binary_search(&self, base_offset: usize, n: usize, target: Value, fuzzy: bool) -> Option<usize> {
        let mut min_idx: usize = 0;
        let mut max_idx = n;

        while max_idx > min_idx {
            let pivot = (min_idx + max_idx) / 2;
            let pivot_int = self.read_interval(base_offset + (pivot as usize) * INTERVAL_SIZE);
            if target >= pivot_int.0 && target < pivot_int.1 {
                return Some(pivot);
            } else if target < pivot_int.0 {
                max_idx = pivot;
            } else {
                min_idx = pivot + 1;
            }
        }
        if fuzzy && min_idx != n {
            Some(min_idx)
        } else {
            None
        }
    }

    fn read_intervals(&self, base_offset: usize, length: usize) -> Vec<Interval> {
        (0..length).map(
            |i| self.read_interval(base_offset + i * INTERVAL_SIZE)
        ).collect()
    }

}

#[pyclass]
struct MmapIntervalSetMapping {
    _impl: _MmapIntervalSetMapping,
}

#[pymethods]
impl MmapIntervalSetMapping {

    fn len(&self) -> PyResult<usize> {
        Ok(self._impl.offsets.len())
    }

    fn get_ids(&self) -> PyResult<Vec<Id>> {
        Ok(self._impl.offsets.keys().map(|k| *k).collect())
    }

    fn has_id(&self, id: Id) -> PyResult<bool> {
        Ok(self._impl.offsets.contains_key(&id))
    }

    // Get the number of intervals for an id
    fn get_interval_count(&self, id: Id) -> PyResult<usize> {
        match self._impl.offsets.get(&id) {
            Some((_, length)) => {
                Ok(*length)
            },
            None => Err(exceptions::IndexError::py_err("id not found")),
        }
    }

    // Get an interval by index
    fn get_interval(&self, id: Id, idx: usize) -> PyResult<Interval> {
        match self._impl.offsets.get(&id) {
            Some((base_offset, length)) => {
                if idx >= *length {
                    return Err(exceptions::IndexError::py_err("index out of range"));
                }
                Ok(self._impl.read_interval(*base_offset + idx * INTERVAL_SIZE))
            },
            None => Err(exceptions::IndexError::py_err("id not found")),
        }
    }

    // Get all intervals for an id
    fn get_intervals(&self, id: Id, no_error: bool) -> PyResult<Vec<Interval>> {
        match self._impl.offsets.get(&id) {
            Some((base_offset, length)) => Ok(self._impl.read_intervals(*base_offset, *length)),
            None => if no_error {
                Ok(vec![])
            } else {
                Err(exceptions::IndexError::py_err("id not found"))
            }
        }
    }

    // Get whether a target is in any of the intervals in the set
    fn is_contained(&self, id: Id, target: Value, no_error: bool) -> PyResult<bool> {
        match self._impl.offsets.get(&id) {
            Some((base_offset, length)) => {
                Ok(self._impl.binary_search(*base_offset, *length, target, false).is_some())
            },
            None => if no_error {
                Ok(false)
            } else {
                Err(exceptions::IndexError::py_err("id not found"))
            }
        }
    }

    // Get whether start and end intersect with any interval in the set
    fn has_intersection_one(&self, id: Id, start: Value, end: Value, no_error: bool) -> PyResult<bool> {
        match self._impl.offsets.get(&id) {
            Some((base_offset, length)) => Ok(
                match self._impl.binary_search(*base_offset, *length, start, true) {
                    Some(min_idx) => {
                        let mut isects = false;
                        let mut i = min_idx;
                        while i < *length {
                            let curr_int = self._impl.read_interval(*base_offset + i * INTERVAL_SIZE);
                            if min(end, curr_int.1) - max(start, curr_int.0) > 0 {
                                isects = true;
                                break;
                            }
                            if curr_int.0 > end {
                                break;
                            }
                            i += 1;
                        }
                        isects
                    },
                    None => false
                }
            ),
            None => if no_error {
                Ok(false)
            } else {
                Err(exceptions::IndexError::py_err("id not found"))
            }
        }
    }

    // Intersect a single interval
    fn intersect_one(&self, id: Id, start: Value, end: Value, no_error: bool) -> PyResult<Vec<Interval>> {
        match self._impl.offsets.get(&id) {
            Some((base_offset, length)) => Ok(
                match self._impl.binary_search(*base_offset, *length, start, true) {
                    Some(min_idx) => {
                        let mut ret = vec![];
                        let mut i = min_idx;
                        while i < *length {
                            let curr_int = self._impl.read_interval(*base_offset + i * INTERVAL_SIZE);
                            if min(end, curr_int.1) - max(start, curr_int.0) > 0 {
                                ret.push(curr_int);
                            }
                            if curr_int.0 > end {
                                break;
                            }
                            i += 1;
                        }
                        ret
                    },
                    None => vec![]
                }
            ),
            None => if no_error {
                Ok(vec![])
            } else {
                Err(exceptions::IndexError::py_err("id not found"))
            }
        }
    }

    // Intersect a sorted list of intervals
    fn intersect(&self, id: Id, intervals: Vec<Interval>, no_error: bool) -> PyResult<Vec<Interval>> {
        match self._impl.offsets.get(&id) {
            Some((base_offset, length)) => {
                let mut res = Vec::new();
                let self_intervals = self._impl.read_intervals(*base_offset, *length);
                let mut i = 0;
                let mut j = 0;
                while i < intervals.len() && j < self_intervals.len() {
                    let a = intervals[i];
                    let b = self_intervals[j];
                    let end = min(a.1, b.1);
                    let start = max(a.0, b.0);
                    if end - start > 0 {
                        res.push((start, end));
                    }
                    if intervals[i].1 <= self_intervals[j].1 {
                        i += 1;
                    } else {
                        j += 1;
                    }
                }
                Ok(res)
            },
            None => if no_error {
                Ok(vec![])
            } else {
                Err(exceptions::IndexError::py_err("id not found"))
            }
        }
    }

    // Minus this from intervals
    fn minus(&self, id: Id, intervals: Vec<Interval>, no_error: bool) -> PyResult<Vec<Interval>> {
        match self._impl.offsets.get(&id) {
            Some((base_offset, length)) => {
                let mut res = Vec::new();
                let self_intervals = self._impl.read_intervals(*base_offset, *length);
                let mut i = 0;
                let mut j = 0;
                let mut mod_a: Option<(Value, Value)> = None;
                while i < intervals.len() && j < self_intervals.len() {
                    if mod_a.is_none() {
                        mod_a = Some(intervals[i])
                    }
                    let a = mod_a.unwrap();
                    let b = self_intervals[j];
                    if a.0 < b.0 {
                        if a.1 <= b.0 {
                            // a before b
                            res.push(a);
                            mod_a = None;
                            i += 1;
                        } else {
                            // a's tail overlaps
                            res.push((a.0, b.0));
                            if a.1 <= b.1 {
                                // rest of a in b
                                mod_a = None;
                                i += 1;
                            } else {
                                // some of a is left
                                mod_a = Some((b.1, a.1));
                                j += 1;
                            }
                        }
                    } else {
                        if a.0 >= b.1 {
                            // b before a
                            j += 1;
                        } else {
                            if a.1 <= b.1 {
                                // a in b
                                mod_a = None;
                                i += 1;
                            } else {
                                // some of a is left
                                mod_a = Some((b.1, a.1));
                                j += 1;
                            }
                        }
                    }
                }
                if mod_a.is_some() {
                    res.push(mod_a.unwrap());
                    i += 1;
                }
                while i < intervals.len() {
                    res.push(intervals[i]);
                    i += 1;
                }
                Ok(res)
            },
            None => if no_error {
                Ok(intervals)
            } else {
                Err(exceptions::IndexError::py_err("id not found"))
            }
        }
    }

    #[new]
    unsafe fn __new__(obj: &PyRawObject, data_file: String) -> PyResult<()> {
        match File::open(&data_file) {
            Ok(data_fh) => {
                let metadata = File::metadata(&data_fh)?;
                let length = metadata.len() as usize;
                if length % mem::size_of::<u32>() != 0 {
                    return Err(exceptions::Exception::py_err(
                               "file length is not a multiple of 4"))
                }
                let mmap = MmapOptions::new().map(&data_fh);
                match mmap {
                    Ok(m) => match parse_offsets(&m) {
                        Some(offsets) => obj.init(|_| MmapIntervalSetMapping {
                            _impl: _MmapIntervalSetMapping {data: m, offsets: offsets}
                        }),
                        None => Err(exceptions::Exception::py_err("cannot parse offsets"))
                    },
                    Err(s) => Err(exceptions::Exception::py_err(s.to_string()))
                }
            },
            Err(s) => Err(exceptions::Exception::py_err(s.to_string()))
        }
    }
}

#[pymodinit]
fn rs_intervalset(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<MmapIntervalSetMapping>()?;
    Ok(())
}
