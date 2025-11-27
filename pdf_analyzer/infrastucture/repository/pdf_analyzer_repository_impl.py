import io
import os
import uuid
import boto3

from typing import List
from sqlalchemy.orm import Session

from config.database.session import SessionLocal

from pdf_analyzer.application.port.pdf_analyzer_repository_port import PDFAnalyzerRepositoryPort
from pdf_analyzer.domain.pdf_analyzer import PDFAnalyzer
from pdf_analyzer.infrastucture.orm.pdf_analyzer_orm import PDFAnalyzerORM


s3_client = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)


class PDFAnalyzerRepositoryImpl(PDFAnalyzerRepositoryPort):
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def save(self, pdf_analyzer: PDFAnalyzer) -> PDFAnalyzer:

        db: Session = SessionLocal()
        try:
            db_obj = PDFAnalyzerORM(
                file_name=pdf_analyzer.file_name,
                s3_key=pdf_analyzer.s3_key,
                uploader_id=pdf_analyzer.uploader_id,
            )
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            # DB에서 받은 id와 timestamp를 도메인 객체에 반영
            pdf_analyzer.id = db_obj.id
            pdf_analyzer.uploaded_at = db_obj.uploaded_at
            pdf_analyzer.updated_at = db_obj.updated_at
        finally:
            db.close()

        return pdf_analyzer

    def find_all(self) -> List[PDFAnalyzer]:
        """
        DB에 있는 모든 문서를 도메인 객체로 반환
        """
        db: Session = SessionLocal()
        pdf_analyzers: List[PDFAnalyzer] = []
        try:
            db_objs = db.query(PDFAnalyzerORM).all()
            for obj in db_objs:
                doc = PDFAnalyzer(
                    file_name=obj.file_name,
                    s3_key=obj.s3_key,
                    uploader_id=obj.uploader_id
                )
                doc.id = obj.id
                doc.uploaded_at = obj.uploaded_at
                doc.updated_at = obj.updated_at
                pdf_analyzers.append(doc)
        finally:
            db.close()

        return pdf_analyzers
