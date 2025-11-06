#!/bin/bash
# fuzz/run_anvil.sh

# A helper script to run a forked Anvil instance in the background.
# Logs are sent to anvil.log.

# NOTE: This expects `anvil` to be in your path.
# You can install it with `foundryup`.

# --fork-url: fork mainnet
# --chain-id 1: required for ape to treat as a mainnet fork
# --block-time 0: mine blocks instantly
# --no-rate-limit: prevent rate limiting for rpc calls
# --unlock: unlock a whale account to seed test accounts

if [ -z "$ETH_RPC_URL" ]; then
    echo "ETH_RPC_URL not set. Please set it to your Ethereum mainnet RPC endpoint."
    exit 1
fi

anvil --fork-url "$ETH_RPC_URL" \
      --chain-id 1 \
      --block-time 0 \
      --no-rate-limit \
      --unlock 0x2fEb1512183545f48f620C19131a31b653b455bC \
      > anvil.log 2>&1 &
