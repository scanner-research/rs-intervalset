/*
* IntervalListMapping
*
* Maintain a mapping from ids to lists of intervals. These intervals can overlap and are defined
* as [start, end). The intervals are sorted by start. Intervals have up to 64bits of payload.
*/
use pyo3::prelude::*;
use pyo3::exceptions;
use std::cmp::{max, min};
use std::collections::HashMap;
use std::mem;
use std::fs::File;
use memmap::{MmapOptions, Mmap};

use common::*;

type IntervalAndPayload = (Value, Value, Payload);

struct _MmapIntervalListMapping {
    data: Mmap,
    offsets: HashMap<Id, (usize, usize)>,
    payload_len: usize
}

impl _MmapIntervalListMapping {

    fn read_interval(&self, i: usize) -> IntervalAndPayload {
        (
            mmap_read_u32(&self.data, i),
            mmap_read_u32(&self.data, i + mem::size_of::<u32>()),
            mmap_read_payload(&self.data, i + 2 * mem::size_of::<u32>(), self.payload_len)
        )
    }

    fn read_intervals(
        &self, base_offset: usize, length: usize, payload_mask: Payload, payload_value: Payload
    ) -> Vec<Interval> {
        let mut ret = Vec::new();
        let interval_payload_size = INTERVAL_SIZE + self.payload_len;
        for i in 0..length {
            let int_and_p = self.read_interval(base_offset + i * interval_payload_size);
            if (payload_mask & int_and_p.2) == payload_value {
                ret.push((int_and_p.0, int_and_p.1));
            }
        }
        ret
    }
}

#[pyclass]
pub struct MmapIntervalListMapping {
    _impl: _MmapIntervalListMapping
}

#[pymethods]
impl MmapIntervalListMapping {

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
    fn get_interval_count(
        &self, id: Id, payload_mask: Payload, payload_value: Payload
    ) -> PyResult<usize> {
        match self._impl.offsets.get(&id) {
            Some((base_offset, length)) => {
                if payload_mask == 0 && payload_value == 0 {
                    Ok(*length)
                } else {
                    Ok(self._impl.read_intervals(
                        *base_offset, *length, payload_mask, payload_value
                    ).len())
                }
            },
            None => Err(exceptions::IndexError::py_err("id not found")),
        }
    }

    fn intersect(
        &self, id: Id, intervals: Vec<Interval>, payload_mask: Payload, payload_value: Payload,
        use_default: bool
    ) -> PyResult<Vec<Interval>> {
        match self._impl.offsets.get(&id) {
            Some((base_offset, length)) => {
                let mut res: Vec<Interval> = Vec::new();
                let self_intervals = self._impl.read_intervals(
                    *base_offset, *length, payload_mask, payload_value);
                let mut i = 0;
                let mut j = 0;
                while i < intervals.len() && j < self_intervals.len() {
                    let a = intervals[i];
                    let b = self_intervals[j];
                    let end = min(a.1, b.1);
                    let start = max(a.0, b.0);
                    if end > start {
                        if res.len() > 0 {
                            let res_len = res.len();
                            let last_res = res[res_len - 1];
                            if min(end, last_res.1) > max(start, last_res.0) {
                                res[res_len - 1] = (min(start, last_res.0), max(end, last_res.1))
                            } else {
                                res.push((start, end));
                            }
                        } else {
                            res.push((start, end));
                        }
                    }
                    if a.1 <= b.1 {
                        i += 1;
                    } else {
                        j += 1;
                    }
                }
                Ok(res)
            },
            None => if use_default {
                Ok(vec![])
            } else {
                Err(exceptions::IndexError::py_err("id not found"))
            }
        }
    }

    fn intersect_sum(
        &self, id: Id, intervals: Vec<Interval>, payload_mask: Payload, payload_value: Payload,
        use_default: bool
    ) -> PyResult<u64> {
        match self._impl.offsets.get(&id) {
            Some((base_offset, length)) => {
                let mut res: u64 = 0;
                let self_intervals = self._impl.read_intervals(
                    *base_offset, *length, payload_mask, payload_value);
                let self_intervals_len = self_intervals.len();
                let mut j_bound = 0;
                for i in 0..intervals.len() {
                    let a = intervals[i];
                    let mut j_bound_end = 0;
                    for j_local in j_bound..self_intervals_len {
                        let b = self_intervals[j_local];
                        let end = min(a.1, b.1);
                        let start = max(a.0, b.0);
                        if end > start {
                            res += (end - start) as u64;
                        }
                        if a.1 <= b.0 {
                            // a before b
                            break;
                        }
                        j_bound_end = max(b.1, j_bound_end);
                        if j_bound_end <= a.1 {
                            j_bound = j_local;
                        }
                    }
                    if j_bound == self_intervals_len {
                        break;
                    }
                }
                Ok(res)
            },
            None => if use_default {
                Ok(0)
            } else {
                Err(exceptions::IndexError::py_err("id not found"))
            }
        }
    }

    #[new]
    unsafe fn __new__(obj: &PyRawObject, data_file: String, payload_len: usize) -> PyResult<()> {
        match File::open(&data_file) {
            Ok(data_fh) => {
                let mmap = MmapOptions::new().map(&data_fh);
                match mmap {
                    Ok(m) => match parse_offsets(&m, payload_len) {
                        Some(offsets) => obj.init(|_| MmapIntervalListMapping {
                            _impl: _MmapIntervalListMapping {
                                data: m, offsets: offsets, payload_len: payload_len
                            }
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
