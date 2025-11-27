from typing import Optional
from datetime import datetime

class Document:
    def __init__(self, file_name: str, s3_key: str, uploader_id: int):
        self.id: Optional[int] = None
        self.file_name = file_name
        self.s3_key = s3_key
        self.uploader_id = uploader_id
        self.uploaded_at: datetime = datetime.utcnow()
        self.updated_at: datetime = datetime.utcnow()
        self.result: Optional[dict] = None

    @classmethod
    def create(cls, file_name: str, s3_key: str, uploader_id: int) -> "Document":
        if not file_name or not s3_key:
            raise ValueError("file_name과 s3_key는 필수입니다")
        return cls(file_name, s3_key, uploader_id)
    
    def update_result(self, result: dict) -> None:
        if not isinstance(result, dict):
            raise TypeError("result는 dict 타입이어야 합니다")

        self.result = result
        self.updated_at = datetime.utcnow()
