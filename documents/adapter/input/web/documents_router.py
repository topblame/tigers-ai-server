from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from documents.application.usecase.document_usecase import DocumentUseCase

documents_router = APIRouter(tags=["documents"])

document_usecase = DocumentUseCase.getInstance()

from account.adapter.input.web.session_helper import get_current_user





@documents_router.post("/register")
async def register_document(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user)
):
    s3_key, file_name = await document_usecase.upload_file_to_s3(file=file)
    doc = document_usecase.register_document(file_name=file_name, s3_key=s3_key, uploader_id=user_id)
    return {
        "id": doc.id,
        "file_name": doc.file_name,
        "s3_key": doc.s3_key,
        "uploader_id": doc.uploader_id,
        "result": doc.result
    }

@documents_router.get("/list")
async def list_documents():
    return document_usecase.list_documents()