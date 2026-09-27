from dataclasses import dataclass

from pyforge.orm import Paginator
from pyforge.resources import Resource


@dataclass
class FakeUser:
    id: int
    name: str
    email: str


class UserResource(Resource):
    def to_dict(self, user: FakeUser) -> dict:
        return {"id": user.id, "name": user.name}


def test_make_transforms_a_single_model() -> None:
    user = FakeUser(id=1, name="Ada", email="ada@example.com")
    assert UserResource.make(user) == {"id": 1, "name": "Ada"}


def test_collection_transforms_a_list() -> None:
    users = [FakeUser(1, "Ada", "a@example.com"), FakeUser(2, "Alan", "b@example.com")]
    assert UserResource.collection(users) == [
        {"id": 1, "name": "Ada"},
        {"id": 2, "name": "Alan"},
    ]


def test_paginated_wraps_data_and_meta() -> None:
    users = [FakeUser(i, f"User {i}", f"u{i}@example.com") for i in range(3)]
    paginator = Paginator(data=users, current_page=1, per_page=10, total=25)

    result = UserResource.paginated(paginator)

    assert result["data"] == [{"id": 0, "name": "User 0"}, {"id": 1, "name": "User 1"}, {"id": 2, "name": "User 2"}]
    assert result["meta"] == {"current_page": 1, "per_page": 10, "total": 25, "last_page": 3}
