class StorageDriver:
    def put(self, path: str, contents: bytes) -> None:
        raise NotImplementedError

    def get(self, path: str) -> bytes:
        raise NotImplementedError

    def delete(self, path: str) -> None:
        raise NotImplementedError

    def exists(self, path: str) -> bool:
        raise NotImplementedError

    def url(self, path: str) -> str:
        raise NotImplementedError
