from pydantic import BaseModel
from typing import List


class DocumentSection(BaseModel):
    number: int
    title: str
    text: str

class Document(BaseModel):
    filename: str
    document_type: str
    content: List[DocumentSection]