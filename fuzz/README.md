# Curve TwoCrypto-NG Local State Fuzzer (Hypothesis + Ape)

Prereqs:
- anvil installed (foundry's anvil)
- Python 3.11+ and virtualenv
- ETH_RPC_URL pointing at an Ethereum provider (Alchemy/Infura)
- POOL_ADDR set to the pool address to fuzz
- (optional) ADMIN_ADDR to impersonate admin operations

Install:
```

python -m venv .venv && source .venv/bin/activate
pip install -r fuzz/requirements.txt

```

Start a fork (in separate terminal):
```

export ETH_RPC_URL="[https://eth-mainnet.alchemyapi.io/v2/KEY](https://eth-mainnet.alchemyapi.io/v2/KEY)"
export POOL_ADDR="0x..."
export ADMIN_ADDR="0x..."    # optional, to allow admin ops
bash fuzz/run_anvil.sh

```

Run the stateful fuzz:
```

cd fuzz
pytest -q tests/test_curve_stateful_fuzz.py::TestCase  -k TestCase -s

```

Failures are saved to `fuzz_failures/` as JSON. Use `scripts/minimize_failure.py` for manual triage.
