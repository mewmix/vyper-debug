# fuzz/tests/test_curve_stateful_fuzz.py
import os
import json
import math
from decimal import Decimal, getcontext
from hypothesis.stateful import RuleBasedStateMachine, rule, precondition, invariant, initialize
from hypothesis import settings, Verbosity
from hypothesis.strategies import integers, lists, just
from ape import accounts, chain, networks
from web3 import Web3, HTTPProvider
from ape.exceptions import TransactionError
from typing import Optional
from eth_abi import encode as abi_encode
from web3.exceptions import ContractLogicError

# Increase decimal precision for comparison to on-chain fixed-point math
getcontext().prec = 80

POOL_ADDR = os.environ.get("POOL_ADDR")
ADMIN_ADDR = os.environ.get("ADMIN_ADDR", None)
FAIL_DIR = os.path.join(os.getcwd(), "fuzz_failures")
os.makedirs(FAIL_DIR, exist_ok=True)

# constants for fuzz bounds (tune to pool decimals)
DX_MIN = 10 ** 3
DX_MAX = 10 ** 22
SMALL = 10 ** 6

# Load ABI from file
script_dir = os.path.dirname(__file__)
abi_path = os.path.join(script_dir, "..", "abi.json")
with open(abi_path) as f:
    POOL_ABI = json.load(f)

ERC20_ABI = [
    {"name":"decimals","outputs":[{"type":"uint8"}],"stateMutability":"view","type":"function","inputs":[]},
    {"name":"symbol","outputs":[{"type":"string"}],"stateMutability":"view","type":"function","inputs":[]},
    {"name":"balanceOf","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function","inputs":[{"name":"a","type":"address"}]},
    {"name":"allowance","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function","inputs":[{"name":"o","type":"address"},{"name":"s","type":"address"}]},
    {"name":"approve","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function","inputs":[{"name":"s","type":"address"},{"name":"a","type":"uint256"}]},
    {"name":"transfer","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function","inputs":[{"name":"t","type":"address"},{"name":"a","type":"uint256"}]}
]

def _get_web3() -> Web3:
    """
    Return a Web3 instance.
    Prefer Ape's connected provider; if not connected yet, fall back to ETH_RPC_URL.
    """
    try:
        # Will raise ProviderNotConnectedError if Ape isn't connected yet
        return networks.provider.web3
    except Exception:
        url = os.environ.get("ETH_RPC_URL")
        if not url:
            raise RuntimeError("ETH_RPC_URL must be set when Ape provider is not connected.")
        return Web3(HTTPProvider(url))

def pool_contract(w3: Web3):
    assert POOL_ADDR, "Set POOL_ADDR env var"
    code = w3.eth.get_code(Web3.to_checksum_address(POOL_ADDR))
    if not code or code == b"":
        raise RuntimeError(
            "No contract code at POOL_ADDR on current provider. "
            "You are not on a mainnet fork. Start anvil with --fork-url and run with --network :local:anvil."
        )
    return w3.eth.contract(address=Web3.to_checksum_address(POOL_ADDR), abi=POOL_ABI)

def as_erc20(w3: Web3, addr: str):
    return w3.eth.contract(address=Web3.to_checksum_address(addr), abi=ERC20_ABI)

@settings(
    max_examples=50,
    stateful_step_count=50,
    verbosity=Verbosity.normal,
    deadline=None,
)
class CurveStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.w3 = _get_web3()
        self.pool = pool_contract(self.w3)
        # record a small local ledger of account balances for invariant checks
        self.actors = [accounts.test_accounts[i] for i in range(min(10, len(accounts.test_accounts)))]
        # pick a default caller
        self.caller = self.actors[0]
        # read coin count
        self.n_coins = 2

        # Get coins and decimals
        self.coins = [self.pool.functions.coins(i).call() for i in range(self.n_coins)]
        assert hasattr(self.pool, "functions"), "self.pool must be a web3 Contract, not ape.contracts.Contract"
        self.decimals = []
        for coin_address in self.coins:
            if coin_address.lower() in ("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE".lower(), "0x0000000000000000000000000000000000000000"):
                self.decimals.append(18)
            else:
                self.decimals.append(as_erc20(self.w3, coin_address).functions.decimals().call())

        # Are we on a dev node where we can actually transact? (fork / local)
        self.tx_ok = self._tx_capable()
        # Optionally seed balances using a whale (only on dev nodes).
        self.funded = self._seed_balances() if self.tx_ok else False

    def _tx_capable(self) -> bool:
        """True when running against Anvil/Hardhat where we can impersonate / set balances."""
        name = (getattr(networks, "provider", None).name or "").lower() if getattr(networks, "provider", None) else ""
        if "anvil" in name or "hardhat" in name:
            return True
        try:
            ver = (self.w3.client_version or "").lower()
            return ("anvil" in ver) or ("hardhat" in ver)
        except Exception:
            return False

    def _impersonate_or_none(self, addr: Optional[str]):
        if not addr:
            return None
        # Try Anvil
        try:
            chain.provider.make_request("anvil_impersonateAccount", [addr])
            return accounts[addr]
        except Exception:
            pass
        # Try Hardhat
        try:
            chain.provider.make_request("hardhat_impersonateAccount", [addr])
            return accounts[addr]
        except Exception:
            pass
        # If already unlocked
        try:
            return accounts[addr]
        except Exception:
            return None

    def _seed_balances(self) -> bool:
        whale_addr = os.environ.get("SETH_WHALE")
        whale = self._impersonate_or_none(whale_addr)
        try:
            # Always make sure test actors have gas
            for a in self.actors:
                chain.provider.set_balance(a.address, 10_000 * 10**18)
        except Exception:
            # Some providers won’t allow balance mutations; continue best-effort.
            pass
        if whale is None:
            return False
        # Transfer ERC20s from whale
        for actor in self.actors:
            for i, coin_address in enumerate(self.coins):
                is_eth = coin_address.lower() in (
                    "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                    "0x0000000000000000000000000000000000000000",
                )
                if is_eth:
                    continue
                # Skip Synthetix synths (sETH, etc.) – transfers may require settlement.
                try:
                    sym = as_erc20(self.w3, coin_address).functions.symbol().call()
                except Exception:
                    sym = ""
                if sym.lower().startswith("s") or coin_address.lower() == "0x5e74c9036fb86bd7ecdcb084a0673efc32ea31cb":
                    continue
                coin = as_erc20(self.w3, coin_address)
                amt = 1_000 * (10**int(self.decimals[i]))
                try:
                    tx = coin.functions.transfer(actor.address, amt).build_transaction({"from": whale.address})
                    self.w3.eth.send_transaction(tx)
                except ContractLogicError:
                    # Non-vanilla ERC20; skip seeding this asset
                    continue
        return True

    @initialize()
    def init_state(self):
        # initial snapshot of pool totals
        self.snapshot_D = self._D()
        self.snapshot_balances = self._balances()

    # ----- helpers to read pool internals -----
    def _D(self):
        try:
            return int(self.pool.functions.D().call())
        except Exception:
            return 0

    def _balances(self):
        bals = []
        for i in range(self.n_coins):
            bals.append(int(self.pool.functions.balances(i).call()))
        return bals

    # ---- helpers: ABI-robust pool calls ----
    def _pool_has_fn(self, name: str, arg_types: list[str]) -> bool:
        """Check if ABI has a function by name + exact arg types."""
        try:
            fns = [f for f in self.pool.functions if f.fn_name == name]
        except Exception:
            fns = []
        for f in fns:
            try:
                sig = f._function.signature
                # crude check: compare "name(type1,type2,...)"
                if sig == f"{name}({','.join(arg_types)})":
                    return True
            except Exception:
                continue
        return False

    def _call_add_liquidity(self, amounts, caller_addr, eth_value: int):
        """
        Try common Curve add_liquidity signatures, provide explicit gas to bypass estimate.
        Order:
          1) (uint256[2], uint256)
          2) (uint256[2], uint256, address)  # receiver
          3) (uint256[2], uint256, bool)     # use_eth
        """
        tx_args = {"from": caller_addr, "value": eth_value, "gas": 2_000_000}

        # v1: (amounts, min_mint)
        if self._pool_has_fn("add_liquidity", ["uint256[2]","uint256"]):
            try:
                return self.pool.functions.add_liquidity(amounts, 0).transact(tx_args)
            except ContractLogicError as e:
                # fallthrough to try other variants
                pass

        # v2: (amounts, min_mint, receiver)
        if self._pool_has_fn("add_liquidity", ["uint256[2]","uint256","address"]):
            try:
                return self.pool.functions.add_liquidity(amounts, 0, caller_addr).transact(tx_args)
            except ContractLogicError:
                pass

        # v3: (amounts, min_mint, use_eth)
        # Important: only set use_eth=True if one coin is native-ETH sentinel in coins[].
        use_eth = eth_value > 0
        if self._pool_has_fn("add_liquidity", ["uint256[2]","uint256","bool"]):
            try:
                return self.pool.functions.add_liquidity(amounts, 0, use_eth).transact(tx_args)
            except ContractLogicError:
                pass

        # If ABI didn’t expose signature metadata, brute-try safely in decreasing likelihood
        # (all within explicit gas; errors stay local to hypothesis run)
        for variant in ("2", "3-addr", "3-bool"):
            try:
                if variant == "2":
                    return self.pool.functions.add_liquidity(amounts, 0).transact(tx_args)
                if variant == "3-addr":
                    return self.pool.functions.add_liquidity(amounts, 0, caller_addr).transact(tx_args)
                if variant == "3-bool":
                    return self.pool.functions.add_liquidity(amounts, 0, use_eth).transact(tx_args)
            except Exception:
                continue
        raise ContractLogicError("add_liquidity: all known signatures reverted (ABI mismatch or balance/allowance).")

    # ----- invariants (checked after each rule) -----
    @invariant()
    def no_negative_balances(self):
        bals = self._balances()
        for b in bals:
            assert b >= 0, f"Negative balance detected: {b}"

    # ----- rules (operations) -----
    @precondition(lambda self: self.tx_ok and self.funded)
    @rule(amounts=lists(integers(10**16, 10**18), min_size=2, max_size=2))
    def add_liquidity(self, amounts):
        caller = self.caller

        eth_index = -1
        for i, coin_address in enumerate(self.coins):
            if coin_address.lower() in ("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE".lower(), "0x0000000000000000000000000000000000000000"):
                eth_index = i
            else:
                as_erc20(self.w3, coin_address).functions.approve(self.pool.address, amounts[i]).transact({"from": caller.address})

        eth_value = amounts[eth_index] if eth_index != -1 else 0
        # Bypass estimateGas by setting 'gas' and try all Curve variants
        self._call_add_liquidity(amounts, caller.address, eth_value)

    @precondition(lambda self: self.tx_ok and self._D() > 0 and self.funded)
    @rule(i=just(0), j=just(1), dx=integers(DX_MIN, 10**17))
    def exchange(self, i, j, dx):
        caller = self.actors[(dx % len(self.actors))]

        eth_value = dx if self.coins[i].lower() in ("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE".lower(), "0x0000000000000000000000000000000000000000") else 0
        if not eth_value:
            as_erc20(self.w3, self.coins[i]).functions.approve(self.pool.address, dx).transact({"from": caller.address})

        self.pool.functions.exchange(i, j, dx, 0).transact({"from": caller.address, "value": eth_value})

    @precondition(lambda self: self.tx_ok and self._D() > 0 and self.funded)
    @rule(lp_amount=integers(min_value=10**16, max_value=10**18), i=integers(0,1))
    def remove_liquidity_one(self, lp_amount, i):
        caller = self.caller
        self.pool.functions.remove_liquidity_one_coin(lp_amount, i, 0).transact({"from": caller.address})

TestStateMachine = CurveStateMachine.TestCase
