
use std::collections::BTreeMap;
use std::mem;
use std::io::Cursor;
use byteorder::{ReadBytesExt, LittleEndian};
use memmap::Mmap;

pub type Id = u32;
pub type Value = u32;
pub type Interval = (Value, Value);
pub type Payload = u64;

pub const INTERVAL_SIZE: usize = 2 * mem::size_of::<Value>();

pub fn mmap_read_u32(m: &Mmap, i: usize) -> u32 {
    let mut rdr = Cursor::new(&m[i..i + mem::size_of::<u32>()]);
    rdr.read_u32::<LittleEndian>().unwrap()
}

pub fn mmap_read_payload(m: &Mmap, i: usize, n: usize) -> Payload {
    let mut res: Payload = 0;
    let bytes: &[u8] = &m[i..i+n];
    for j in 0..n {
        res |= (bytes[j] << (8 * j)) as u64;
    }
    res
}

pub fn parse_offsets(m: &Mmap, payload_len: usize) -> Option<BTreeMap<Id, (usize, usize)>> {
    let mut i = 0;
    let mut id_offsets: BTreeMap<Id, (usize, usize)> = BTreeMap::new();
    while i < m.len() {
        let id = mmap_read_u32(m, i) as Id;
        let n = mmap_read_u32(m, i + mem::size_of::<Id>()) as usize;
        i += mem::size_of::<Id>() + mem::size_of::<u32>();
        id_offsets.insert(id, (i, n));
        i += n * (INTERVAL_SIZE + payload_len);
    }
    if i != m.len() {
        None
    } else {
        Some(id_offsets)
    }
}
