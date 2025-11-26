import os
import boto3

from fastapi import UploadFile, HTTPException

from typing import List
from documents.domain.document import Document
from documents.infrastructure.repository.document_repository_impl import DocumentRepositoryImpl



class DocumentUseCase:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.repository = DocumentRepositoryImpl.getInstance()

        return cls.__instance

    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = cls()

        return cls.__instance

    async def upload_file_to_s3(self, file: UploadFile):
        if file is None:
            raise HTTPException(status_code=404, detail="File Not Found")
        
        file_key, filename = await self.repository.upload(file=file)
        if not file_key or not filename:
            raise HTTPException(status_code=404, detail="Upload Failed")
        return file_key, filename


    def register_document(self, file_name: str, s3_key: str, uploader_id: int) -> Document:
        doc = Document.create(file_name, s3_key, uploader_id)
        return self.repository.save(doc)

    def list_documents(self) -> List[Document]:
        return self.repository.find_all()
