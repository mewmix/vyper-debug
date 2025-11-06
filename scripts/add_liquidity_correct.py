# scripts/add_liquidity_correct.py
import os
from ape import accounts, Contract, chain
from ape.exceptions import ContractLogicError

POOL_ADDR = os.environ["POOL_ADDR"]
SENDER = accounts.test_accounts[0]

ETH_SENTINELS = {
    "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE".lower(),
    "0x0000000000000000000000000000000000000000",
    "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # just in case checksummed
}

ERC20_ABI = [
    {"name":"decimals","outputs":[{"type":"uint8"}],"stateMutability":"view","type":"function","inputs":[]},
    {"name":"symbol","outputs":[{"type":"string"}],"stateMutability":"view","type":"function","inputs":[]},
    {"name":"balanceOf","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function","inputs":[{"name":"a","type":"address"}]},
    {"name":"allowance","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function","inputs":[{"name":"o","type":"address"},{"name":"s","type":"address"}]},
    {"name":"approve","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function","inputs":[{"name":"s","type":"address"},{"name":"a","type":"uint256"}]},
]

def is_eth_addr(addr: str) -> bool:
    if not addr:
        return False
    return addr.lower() in ETH_SENTINELS

def as_erc20(addr):
    return Contract(addr, abi=ERC20_ABI)

def get_coins(pool):
    # Try common layouts: coins(i) or tokens(i)
    for getter in ("coins", "tokens"):
        if hasattr(pool, getter):
            try:
                c0 = getattr(pool, getter)(0)
                c1 = getattr(pool, getter)(1)
                return [c0, c1], getter
            except Exception:
                pass
    # Some deployments store in arrays; last resort
    return [pool.coins[0], pool.coins[1]], "coins[]"

def get_decimals(pool, coins):
    decs = []
    for i, c in enumerate(coins):
        if is_eth_addr(c):
            decs.append(18)
        else:
            decs.append(as_erc20(c).decimals())
    return decs

def scale(human, decimals):
    return int(human * (10 ** decimals))

def main():
    pool = Contract(POOL_ADDR)
    coins, src = get_coins(pool)
    decs = get_decimals(pool, coins)

    print(f"POOL: {pool.address}")
    print(f"coins via {src}: {coins}")
    print(f"decimals: {decs}")

    # Choose sane deposit: 0.5 units of each coin in native units
    # (adjust HUMAN_AMOUNTS if you want)
    HUMAN_AMOUNTS = [0.5, 0.5]
    amounts = [scale(HUMAN_AMOUNTS[i], decs[i]) for i in range(2)]

    # Identify which index (if any) is ETH sentinel
    eth_index = None
    for i, c in enumerate(coins):
        if is_eth_addr(c):
            eth_index = i
            break

    # Balances & allowances
    for i, c in enumerate(coins):
        if is_eth_addr(c):
            bal = SENDER.balance
            print(f"[{i}] ETH balance: {bal}")
        else:
            token = as_erc20(c)
            bal = token.balanceOf(SENDER)
            allowance = token.allowance(SENDER, pool.address)
            sym = ""
            try:
                sym = token.symbol()
            except Exception:
                pass
            print(f"[{i}] {sym or c} balance={bal} allowance_to_pool={allowance}")

    # Approvals for ERC20 legs
    for i, c in enumerate(coins):
        if is_eth_addr(c):
            continue
        token = as_erc20(c)
        need = amounts[i]
        current = token.allowance(SENDER, pool.address)
        if current < need:
            print(f"approve {c} for {need}")
            token.approve(pool.address, need, sender=SENDER)

    # Dry-run: calc_token_amount (if exposed) to verify non-revert & slippage
    try:
        minted = pool.calc_token_amount(amounts, True)
        print(f"calc_token_amount(amounts, True) -> {minted}")
        min_mint = int(minted * 0.99)  # 1% slippage guard
    except Exception:
        # Fallback: just use 0 min mint
        min_mint = 0
        print("calc_token_amount unavailable; using min_mint_amount=0")

    # Determine msg.value
    eth_value = 0
    if eth_index is not None:
        eth_value = amounts[eth_index]
        print(f"ETH leg at index {eth_index}: sending msg.value={eth_value}")

    # Try both signatures: (amounts,min,receiver) then (amounts,min)
    try:
        print("calling add_liquidity(amounts, min_mint, receiver)")
        tx = pool.add_liquidity(amounts, min_mint, SENDER.address, sender=SENDER, value=eth_value)
    except ContractLogicError:
        print("retry add_liquidity(amounts, min_mint)")
        tx = pool.add_liquidity(amounts, min_mint, sender=SENDER, value=eth_value)

    print(f"OK: add_liquidity gas_used={tx.gas_used}")
