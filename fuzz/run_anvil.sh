#!/usr/bin/env bash
set -euo pipefail

: "${ETH_RPC_URL:?Set ETH_RPC_URL to a mainnet provider (Alchemy/Infura)}"
: "${POOL_ADDR:?Set POOL_ADDR to the pool you want to fuzz (0x...)}"
: "${ADMIN_ADDR:?Optional: ADMIN_ADDR to impersonate (if pool has admin functions)}"

# Start anvil forking mainnet; unlock admin for impersonation
ANVIL_CMD="anvil --fork-url $ETH_RPC_URL --chain-id 1 --block-time 0 --fork-block-number latest"
if [ -n "${ADMIN_ADDR:-}" ]; then
  ANVIL_CMD="$ANVIL_CMD --unlock ${ADMIN_ADDR}"
fi

echo "Starting anvil (fork) with:"
echo "  POOL_ADDR = $POOL_ADDR"
echo "  ADMIN_ADDR = ${ADMIN_ADDR:-<none>}"
echo "$ANVIL_CMD"
exec $ANVIL_CMD
