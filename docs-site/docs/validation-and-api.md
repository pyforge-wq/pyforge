# Validation & API Resources

## `FormRequest`

```python
from pyforge import FormRequest

class CreateUserRequest(FormRequest):
    rules = {
        "name": "required|string|max:255",
        "email": "required|email|unique:users",
        "password": "required|min:8|confirmed",
    }
```

```python
class UserController:
    async def store(self, request: CreateUserRequest) -> dict:
        return {"created": request.validated()}
```

A controller (or plain function route) parameter annotated with a
`FormRequest` subclass and no explicit default is turned into a FastAPI
dependency **automatically** by `Router` — no `Depends(...)` needed. On
failure it raises `HTTPException(422, detail={"errors": {field: [messages]}})`
before your handler runs.

### Supported rules

| Rule | Meaning |
|---|---|
| `required` | Field must be present and non-empty |
| `nullable` | Field may be `None`/absent |
| `string`, `integer`, `numeric`, `boolean` | Type check |
| `email`, `url` | Format check |
| `min:N`, `max:N` | Length (strings) or value (numbers) bound |
| `in:a,b,c` | Value must be one of the listed options |
| `confirmed` | Compares against a `<field>_confirmation` field |
| `unique:table[,column]` | Checked against `pyforge.orm.Base.metadata`'s tables — works without importing the specific `Model` class |

Native Pydantic models work exactly as they always have in FastAPI —
`FormRequest` is an alternative for pipe-separated string rules, not a
replacement. Mix both freely across different endpoints.

## Generate one

```bash
pyforge make:request CreateUser
```

## API resources: `Resource`

Transform a model (or a list, or a page of them) into a JSON-ready shape,
independent of your ORM columns:

```python
from pyforge import Resource

class UserResource(Resource):
    def to_dict(self, user) -> dict:
        return {"id": user.id, "name": user.name}
```

```python
UserResource.make(user)                                    # -> dict
UserResource.collection(users)                              # -> list[dict]
UserResource.paginated(User.query().paginate(per_page=20))  # -> {"data": [...], "meta": {...}}
```

`paginated(...)` is the direct bridge from `QueryBuilder.paginate(...)`'s
`Paginator` (see [Database & ORM](database.md#pagination)) to the
`{"data": [...], "meta": {...}}` envelope:

```python
class PostController:
    async def index(self) -> dict:
        page = Post.query().order_by("created_at", "desc").paginate(per_page=20)
        return PostResource.paginated(page)
```

## Generate one

```bash
pyforge make:resource User
```

## Centralized error handling

Every `PyForge` app registers two exception handlers automatically:

| Exception | Response |
|---|---|
| `pyforge.orm.ModelNotFoundError` (raised by `Model.find_or_fail`) | `404`, `{"message": str(exc)}` |
| `pyforge.core.PyForgeError` (and subclasses) | `500`, `{"message": str(exc)}` if `config("app.debug")` is true, else `{"message": "Internal Server Error"}` |

```python
class PostController:
    async def show(self, id: int) -> dict:
        post = Post.find_or_fail(id)   # -> 404 automatically if missing
        return {"id": post.id, "title": post.title}
```

Register more handlers exactly the way you would in plain FastAPI — these
two are just what PyForge itself raises:

```python
app.fastapi.add_exception_handler(ValueError, my_handler)
```

!!! danger "`APP_DEBUG` in production"
    Keep `APP_DEBUG=false` in production — it gates whether the `500`
    response includes real exception detail. See [Security](security.md)
    and [Deployment](deployment.md).
