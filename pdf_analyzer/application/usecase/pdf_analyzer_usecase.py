import os
import boto3

from fastapi import UploadFile, HTTPException

from typing import List
from pdf_analyzer.infrastucture.repository.pdf_analyzer_repository_impl import PDFAnalyzerRepositoryImpl



class PDFAnalyzerUseCase:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.repository = PDFAnalyzerRepositoryImpl.getInstance()

        return cls.__instance

    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = cls()

        return cls.__instance


