# Vyper Gas and Hashing Experiments

This project contains a series of experiments in Vyper, designed to explore gas usage and hashing behavior under different conditions. Each experiment consists of a Vyper contract and a corresponding Python test file.

## Experiments

### 1. Keccak256 with `Bytes[M]`

- **Contract:** `contracts/KecBytesM.vy`
- **Test:** `tests/test_kec_bytesM.py`

This experiment compares the gas cost of `keccak256` on `Bytes[16]`, `Bytes[31]`, and `Bytes[33]`.

**Findings:**
- The gas cost increases as the size of the input bytes increases.
- The hashes of different inputs are unique.

### 2. Keccak256 with `bytes32` vs. `Bytes[32]`

- **Contract:** `contracts/KecFixed32.vy`
- **Test:** `tests/test_kec_fixed32.py`

This experiment compares the gas cost of `keccak256` on a `bytes32` input versus a `Bytes[32]` input.

**Findings:**
- Hashing a `bytes32` is more gas-efficient than hashing a `Bytes[32]`.

### 3. Map Key Packing

- **Contract:** `contracts/MapKeyPacking.vy`
- **Test:** `tests/test_map_key_packing.py`

This experiment demonstrates how to pack multiple `uint256` values into a single `bytes32` key for a `HashMap`.

**Findings:**
- This is a common pattern to save storage costs, but it's important to be aware of potential hash collisions. The test `test_collision_guard` shows that with a good hashing algorithm, the risk of collisions is low.

### 4. Memory Fuzzing

- **Contract:** `contracts/MemFuzz.vy`
- **Test:** `tests/test_mem_fuzz.py`

This experiment tests the Vyper memory allocator and copy paths by hashing a dynamic array of `Bytes` with varying sizes.

**Findings:**
- The test `test_gas_ceiling` sets a gas limit for the `run` function, ensuring that the memory operations are within a reasonable gas budget.

### 5. Misaligned Slices

- **Contract:** `contracts/MisalignSlice.vy`
- **Test:** `tests/test_misalign_slice.py`

This experiment explores the gas cost of `keccak256` on slices of `Bytes` that are not aligned to 32-byte words.

**Findings:**
- The gas cost of hashing a 33-byte slice is greater than or equal to the gas cost of hashing a 31-byte slice.

## How to Run the Experiments

1. **Install eth-ape:**
   ```bash
   pip install eth-ape
   ```
2. **Install the Vyper plugin:**
   ```bash
   pip install ape-vyper
   ```
3. **Run the tests:**
   ```bash
   ape test
   ```
