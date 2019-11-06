#![feature(specialization)]

extern crate pyo3;
extern crate memmap;
extern crate byteorder;

mod common;
mod isetmap;
mod ilistmap;

use pyo3::prelude::{PyModule, PyResult, pymodule};
use pyo3::Python;
use isetmap::MmapIntervalSetMapping;
use ilistmap::MmapIntervalListMapping;

#[pymodule]
fn rs_intervalset(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_class::<MmapIntervalSetMapping>()?;
    m.add_class::<MmapIntervalListMapping>()?;
    Ok(())
}
