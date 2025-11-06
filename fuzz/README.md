# Curve Pool Fuzzing Suite

This directory contains a stateful fuzzing suite for Curve pools, using Hypothesis and `eth-ape`.

## Running the Fuzzer

There are two ways to run the fuzzer:

**1. Live RPC (Read-Only Invariants)**

This mode runs only the read-only invariants against a live mainnet RPC. It's useful for quickly checking for basic inconsistencies without needing to set up a forked environment.

```bash
. .venv/bin/activate
export ETH_RPC_URL="<YOUR_ALCHEMY_MAINNET_RPC_URL>"
export POOL_ADDR="0xc5424b857f758e906013f3555dad202e4bdb4567"
unset ADMIN_ADDR SETH_WHALE
cd fuzz
pytest -q tests/test_curve_stateful_fuzz.py -s
```

**2. Dev Fork (Full Stateful Fuzz)**

This mode runs the full stateful fuzzing suite against a forked Anvil instance. This allows for testing of state-changing operations like `add_liquidity`, `exchange`, and `remove_liquidity_one`.

First, start the forked Anvil instance:

```bash
# In one shell
./run_anvil.sh
```

Then, in another shell, run the fuzzer:

```bash
# In another shell
. .venv/bin/activate
export POOL_ADDR="0xc5424b857f758e906013f3555dad202e4bdb4567"
export SETH_WHALE="0x06920C9fC643De77B99cB7670A944AD31eaAA260" # A whale with stETH and ETH
ape test --network :local:foundry -q fuzz/tests/test_curve_stateful_fuzz.py -s
```
