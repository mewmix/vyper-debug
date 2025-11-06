# fuzz/tests/test_curve_stateful_fuzz.py
import os
import json
import math
from decimal import Decimal, getcontext
from hypothesis.stateful import RuleBasedStateMachine, rule, precondition, invariant, initialize
from hypothesis import settings, Verbosity
from ape import Contract, accounts, chain, networks
from ape.exceptions import TransactionError

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

# Helper: load contract
def pool_contract():
    assert POOL_ADDR, "Set POOL_ADDR env var"
    return Contract(POOL_ADDR)

# Helper: safe call with signature variants
def try_call(fn, *args, sender=None, **kwargs):
    try:
        return fn(*args, sender=sender, **kwargs)
    except Exception as e:
        # Bubble up to harness to record
        raise

# Helper: convert raw bytes->Decimal price using high precision arithmetic
def safe_decimal(n):
    return Decimal(n)

class CurveStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.pool = pool_contract()
        # record a small local ledger of account balances for invariant checks
        self.actors = [accounts.test_accounts[i] for i in range(min(10, len(accounts.test_accounts)))]
        # pick a default caller
        self.caller = self.actors[0]
        # read coin count
        try:
            self.n_coins = self.pool.N_COINS()  # some pools expose N_COINS
        except Exception:
            # fallback to 2
            self.n_coins = 2

    @initialize()
    def init_state(self):
        # initial snapshot of pool totals
        self.snapshot_D = self._D()
        self.snapshot_balances = self._balances()

    # ----- helpers to read pool internals -----
    def _D(self):
        try:
            return int(self.pool.D())
        except Exception:
            # some forks might call D() as view(uint256) or variable; try public var
            return int(self.pool.D) if hasattr(self.pool, "D") else 0

    def _balances(self):
        # return list of token balances as integers
        bals = []
        for i in range(self.n_coins):
            try:
                b = int(self.pool.balances(i))
            except Exception:
                # other pools expose balances array or use coins() mapping; try variations
                try:
                    b = int(self.pool.balances[i])
                except Exception:
                    b = 0
            bals.append(b)
        return bals

    def _virtual_price(self):
        # if pool exposes get_virtual_price or similar
        try:
            return Decimal(self.pool.get_virtual_price())
        except Exception:
            return None

    # ----- invariants (checked after each rule) -----
    @invariant()
    def no_negative_balances(self):
        bals = self._balances()
        for b in bals:
            assert b >= 0, f"Negative balance detected: {b}"

    @invariant()
    def D_monotonic_non_negative(self):
        d = self._D()
        assert d >= 0, f"D negative {d}"

    # A less strict invariant: D shouldn't drop dramatically absent admin/op changes
    @invariant()
    def D_not_spiking_down(self):
        d = self._D()
        # allow small tolerances from fees; flag large drops (>1%)
        prev = getattr(self, "snapshot_D", None)
        if prev:
            # if D decreased by >1% flag as suspicious
            if d < prev * 0.99:
                raise AssertionError(f"D dropped too much: {prev} -> {d}")

    # ----- rules (operations) -----
    @precondition(lambda self: True)
    @rule(i=0, j=1, dx=__import__("hypothesis.strategies").integers(DX_MIN, DX_MAX))
    def exchange(self, i, j, dx):
        # pick a caller
        caller = self.actors[(dx % len(self.actors))]
        pool = self.pool

        # read D before
        D0 = self._D()
        try:
            # try both signatures: (i,j,dx,min_dy,receiver) or (i,j,dx,min_dy)
            try:
                tx = pool.exchange(i, j, dx, 0, caller, sender=caller)
            except Exception:
                tx = pool.exchange(i, j, dx, 0, sender=caller)
        except TransactionError as e:
            # record fail and raise to get reported
            self._save_failure("exchange", dict(i=i, j=j, dx=dx), str(e))
            raise

        # post checks
        D1 = self._D()
        # expect no negative D and not extreme downward moves
        if D1 < 0:
            self._save_failure("D_negative_after_exchange", dict(i=i, j=j, dx=dx), f"{D0}->{D1}")
            raise AssertionError("D negative after exchange")
        if D1 < D0 * Decimal("0.99"):
            # suspicious drop >1%
            self._save_failure("D_drop", dict(i=i, j=j, dx=dx), f"{D0}->{D1}")
            raise AssertionError(f"D dropped >1% after exchange {D0}->{D1}")

    @precondition(lambda self: True)
    @rule(amounts=__import__("hypothesis.strategies").lists(__import__("hypothesis.strategies").integers(SMALL, 10**18), min_size=2, max_size=2))
    def add_liquidity(self, amounts):
        pool = self.pool
        caller = self.actors[0]
        try:
            # try both signatures (many pools accept receiver)
            try:
                tx = pool.add_liquidity(amounts, 0, caller, sender=caller)
            except Exception:
                tx = pool.add_liquidity(amounts, 0, sender=caller)
        except TransactionError as e:
            self._save_failure("add_liquidity", dict(amounts=amounts), str(e))
            raise

        # quick post-checks
        new_bals = self._balances()
        for b in new_bals:
            if b < 0:
                self._save_failure("neg_bal_add_liq", dict(amounts=amounts), f"{new_bals}")
                raise AssertionError("Negative balances after add_liquidity")

    @precondition(lambda self: True)
    @rule(lp_amount=__import__("hypothesis.strategies").integers(min_value=1, max_value=10**18), i=__import__("hypothesis.strategies").integers(0,1))
    def remove_liquidity_one(self, lp_amount, i):
        pool = self.pool
        caller = self.actors[0]
        if not hasattr(pool, "remove_liquidity_one_coin"):
            return
        try:
            try:
                tx = pool.remove_liquidity_one_coin(lp_amount, i, 0, caller, sender=caller)
            except Exception:
                tx = pool.remove_liquidity_one_coin(lp_amount, i, 0, sender=caller)
        except TransactionError as e:
            self._save_failure("remove_liquidity_one_coin", dict(lp_amount=lp_amount, i=i), str(e))
            raise

        # post-check balances
        bals = self._balances()
        for b in bals:
            if b < 0:
                self._save_failure("neg_bal_after_remove", dict(lp_amount=lp_amount, i=i), str(bals))
                raise AssertionError("Negative balance after remove")

    @precondition(lambda self: ADMIN_ADDR is not None)
    @rule(new_A=__import__("hypothesis.strategies").integers(1, 10**6))
    def ramp_A(self, new_A):
        pool = self.pool
        # impersonate admin if unlocked in anvil
        admin = accounts.test_accounts[0] if ADMIN_ADDR is None else accounts.at(ADMIN_ADDR)
        try:
            if hasattr(pool, "ramp_A_gamma"):
                pool.ramp_A_gamma(new_A, new_A, chain.blocks[-1].timestamp + 3600, sender=admin)
            elif hasattr(pool, "ramp_A"):
                pool.ramp_A(new_A, chain.blocks[-1].timestamp + 3600, sender=admin)
        except Exception as e:
            self._save_failure("ramp_A_fail", dict(new_A=new_A), str(e))
            raise

    # utility: persist failing case and basic context
    def _save_failure(self, name, params, info):
        fname = os.path.join(FAIL_DIR, f"fail_{name}_{len(os.listdir(FAIL_DIR))}.json")
        obj = {
            "name": name,
            "params": params,
            "info": str(info),
            "block": chain.blocks[-1].number,
        }
        with open(fname, "w") as f:
            json.dump(obj, f, indent=2)

# Hypothesis settings tuned for stress and traceability
TestStateMachine = CurveStateMachine.TestCase
settings(max_examples=200, stateful_step_count=200, verbosity=Verbosity.normal)
