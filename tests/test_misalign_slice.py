def test_slices_ok(project, accounts):
    c = project.MisalignSlice.deploy(sender=accounts[0])
    buf = bytes(range(65))
    _ = c.s31(buf, sender=accounts[0]).gas_used
    _ = c.s33(buf, sender=accounts[0]).gas_used

def test_s33_vs_s31_gas(project, accounts):
    c = project.MisalignSlice.deploy(sender=accounts[0])
    buf = bytes(range(65))
    g31 = c.s31(buf, sender=accounts[0]).gas_used
    g33 = c.s33(buf, sender=accounts[0]).gas_used
    assert g33 >= g31