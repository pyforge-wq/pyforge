# Minimal example

A single-file PyForge app — no `pyforge new` scaffold — demonstrating all
four levels of usage described in
[docs/architecture/03-public-api-design.md](../../docs/architecture/03-public-api-design.md#four-levels-of-usage)
in one small file.

```bash
pip install pyforge-framework
cd examples/minimal
uvicorn main:app --reload
```

Then:

```bash
curl http://localhost:8000/greet/Ada
curl http://localhost:8000/protected/greet/Ada          # 401
curl -H "X-API-Key: demo-key" http://localhost:8000/protected/greet/Ada
curl http://localhost:8000/health
```
