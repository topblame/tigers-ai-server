import io
import os
import uuid
import boto3

from typing import List
from sqlalchemy.orm import Session

from config.database.session import SessionLocal

from pdf_analyzer.application.port.pdf_analyzer_repository_port import PDFAnalyzerRepositoryPort





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

