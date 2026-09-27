"""Minimal PyForge example — no project generator involved.

Shows the four levels of usage from the same tiny app:
  1. beginner:      a controller resolved through the container
  2. intermediate:  a route group with named middleware
  3. advanced:       an explicit container binding (an interface swapped for
                      an implementation)
  4. FastAPI expert: a route registered directly on the FastAPI app

Run with:
    pip install pyforge-framework
    uvicorn examples.minimal.main:app --reload --app-dir .
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from pyforge import PyForge, Router, container


class Greeter:
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"


class LoudGreeter(Greeter):
    def greet(self, name: str) -> str:
        return f"HELLO, {name.upper()}!"


# 3. Advanced: bind an interface to a concrete implementation.
container.bind(Greeter, LoudGreeter)


class GreetingController:
    def __init__(self, greeter: Greeter) -> None:  # autowired by the container
        self.greeter = greeter

    async def show(self, name: str) -> dict:
        return {"message": self.greeter.greet(name)}


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != "demo-key":
        raise HTTPException(status_code=401, detail="missing or invalid X-API-Key")


app = PyForge(title="PyForge Minimal Example")
app.middleware.register("api-key", require_api_key)

router = Router()

# 1. Beginner: a controller action, resolved through the container.
router.get("/greet/{name}", GreetingController.show, name="greet")

# 2. Intermediate: a route group with named middleware.
with router.group(prefix="/protected", middleware=["api-key"]) as group:
    group.get("/greet/{name}", GreetingController.show)

app.register_routes(router)


# 4. FastAPI expert: register a route directly on the underlying FastAPI app.
@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
