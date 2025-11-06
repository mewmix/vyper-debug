@external
def s33(x: Bytes[65]) -> bytes32:
    y: Bytes[33] = slice(x, 1, 33)
    return keccak256(y)

@external
def s31(x: Bytes[65]) -> bytes32:
    y: Bytes[31] = slice(x, 1, 31)
    return keccak256(y)