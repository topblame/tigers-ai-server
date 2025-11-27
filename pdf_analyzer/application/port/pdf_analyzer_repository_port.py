from abc import ABC, abstractmethod
from typing import List
from pdf_analyzer.domain.pdf_analyzer import PDFAnalyzer

class PDFAnalyzerRepositoryPort(ABC):
    @abstractmethod
    async def upload(self):
        pass
        
    @abstractmethod
    def save(self, pdf_analyzer: PDFAnalyzer) -> PDFAnalyzer:
        pass

    @abstractmethod
    def find_all(self) -> List[PDFAnalyzer]:
        pass
