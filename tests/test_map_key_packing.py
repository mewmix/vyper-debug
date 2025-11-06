def test_ordering(project, accounts):
    c = project.MapKeyPacking.deploy(sender=accounts[0])
    c.put(1, 2, 42, sender=accounts[0])
    assert c.get(1, 2) == 42
    assert c.get(2, 1) == 0

def test_collision_guard(project, accounts):
    c = project.MapKeyPacking.deploy(sender=accounts[0])
    c.put(0, 1, 1, sender=accounts[0])
    c.put(1 << 255, 1, 2, sender=accounts[0])
    assert c.get(0, 1) == 1
    assert c.get(1 << 255, 1) == 2