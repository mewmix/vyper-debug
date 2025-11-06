# Drives allocator/copy paths by hashing caller-supplied chunks with sizes 31/32/33.
 @external
def run(chunks: DynArray[Bytes[64], 64]) -> bytes32:
    acc: bytes32 = empty(bytes32)
    for c in chunks:
        # hash the exact slice length of each provided chunk
        acc = keccak256(c)
    return acc