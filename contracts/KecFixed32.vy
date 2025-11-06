 @external
def h32(x: bytes32) -> bytes32:
    return keccak256(x)

 @external
def h_dyn(x: Bytes[32]) -> bytes32:
    return keccak256(x)