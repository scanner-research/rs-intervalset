#![feature(specialization)]

extern crate pyo3;
extern crate memmap;
extern crate byteorder;

mod common;
mod isetmap;
mod ilistmap;

use pyo3::prelude::{Python, PyModule, PyResult, pymodinit};
use isetmap::MmapIntervalSetMapping;
use ilistmap::MmapIntervalListMapping;

#[pymodinit]
fn rs_intervalset(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<MmapIntervalSetMapping>()?;
    m.add_class::<MmapIntervalListMapping>()?;
    Ok(())
}
