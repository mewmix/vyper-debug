def make_chunks():
    chunks = []
    for i in range(64):
        size = 31 + (i % 3)  # 31,32,33
        chunks.append(bytes([(j + i) % 256 for j in range(size)]))
    return chunks

def test_runs(project, accounts):
    c = project.MemFuzz.deploy(sender=accounts[0])
    out = c.run(make_chunks(), sender=accounts[0]).return_value
    assert isinstance(out, bytes) and len(out) == 32

def test_gas_ceiling(project, accounts):
    c = project.MemFuzz.deploy(sender=accounts[0])
    r = c.run(make_chunks(), sender=accounts[0])
    assert r.gas_used < 2_000_000