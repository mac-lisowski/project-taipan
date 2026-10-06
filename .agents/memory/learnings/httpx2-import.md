# httpx2 imports as httpx

Dev dep is `httpx2`, an httpx fork. starlette's TestClient imports it
as `httpx` automatically; plain `import httpx` fails. Not a typo.
