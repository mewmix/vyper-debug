struct K:
    a: uint256
    b: uint256

s: HashMap[bytes32, uint256]

@internal
def pack(a: uint256, b: uint256) -> bytes32:
    # 32-byte ABI words, big-endian; concat yields Bytes[64]
    return keccak256(concat(convert(a, bytes32), convert(b, bytes32)))

@external
def put(a: uint256, b: uint256, v: uint256):
    self.s[self.pack(a, b)] = v

@external
def get(a: uint256, b: uint256) -> uint256:
    return self.s[self.pack(a, b)]