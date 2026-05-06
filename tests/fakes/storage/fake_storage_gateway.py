from app.application.storage.ports import StorageGateway, UploadedFile


class FakeStorageGateway(StorageGateway):
    def __init__(self) -> None:
        self.uploads: list[dict] = []
        self.deletes: list[dict] = []

    async def upload(self, *, bucket: str, key: str, data: bytes, content_type: str) -> UploadedFile:
        self.uploads.append({"bucket": bucket, "key": key, "size": len(data), "content_type": content_type})
        return UploadedFile(
            key=key,
            url=f"http://localhost:9000/{bucket}/{key}",
            size=len(data),
            content_type=content_type,
        )

    async def delete(self, *, bucket: str, key: str) -> None:
        self.deletes.append({"bucket": bucket, "key": key})
