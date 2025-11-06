 @external
def h16(x: Bytes[16]) -> bytes32:
    return keccak256(x)

 @external
def h31(x: Bytes[31]) -> bytes32:
    return keccak256(x)

 @external
def h33(x: Bytes[33]) -> bytes32:
    return keccak256(x)