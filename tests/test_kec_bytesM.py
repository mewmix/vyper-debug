def pad(n): return bytes([0xAB]) * n

def test_values(project, accounts):
    c = project.KecBytesM.deploy(sender=accounts[0])
    assert c.h16(pad(16)) == c.h31(pad(31))
    assert c.h33(pad(33)) != c.h31(pad(31))

def test_gas_trend(project, accounts):
    c = project.KecBytesM.deploy(sender=accounts[0])
    g16 = c.h16(pad(16), sender=accounts[0]).gas_used
    g31 = c.h31(pad(31), sender=accounts[0]).gas_used
    g33 = c.h33(pad(33), sender=accounts[0]).gas_used
    assert g16 <= g31 <= g33