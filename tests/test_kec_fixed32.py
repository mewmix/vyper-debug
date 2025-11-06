def test_hash_equivalence(project, accounts):
    c = project.KecFixed32.deploy(sender=accounts[0])
    x = (0x11).to_bytes(32, "big")
    assert c.h32(x, sender=accounts[0]).return_value == c.h_dyn(x, sender=accounts[0]).return_value

def test_gas_delta(project, accounts):
    c = project.KecFixed32.deploy(sender=accounts[0])
    x = (0x22).to_bytes(32, "big")
    r_fast = c.h32(x, sender=accounts[0])
    r_dyn  = c.h_dyn(x, sender=accounts[0])
    assert r_fast.gas_used <= r_dyn.gas_used