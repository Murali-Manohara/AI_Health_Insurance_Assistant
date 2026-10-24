from typing import Optional, Any
from pydantic import BaseModel, Field

class TextBlock(BaseModel):
    text: str
    page_number: int
    bbox: Optional[tuple[float, float, float, float]] = None
    is_heading: bool = False
    heading_level: int = 0

class ListItem(BaseModel):
    item_text: str
    item_index: int
    page_number: int

class TableRow(BaseModel):
    cells: list[str]
    is_header: bool = False

class StructuredTable(BaseModel):
    table_id: str
    title: str
    headers: list[str]
    rows: list[list[str]]
    page_start: int
    page_end: int
    section_context: str = ""
    footnotes: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)

class CalculationBlock(BaseModel):
    calc_id: str
    title: str
    formula: str
    variables: dict[str, str] = Field(default_factory=dict)
    inputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[str] = Field(default_factory=list)
    result: str
    units_or_currency: str = "INR"
    limits: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    page_number: int
    arithmetic_valid: Optional[bool] = None

class SubsectionNode(BaseModel):
    subsection_id: str
    number: str
    title: str
    page_start: int
    page_end: int
    paragraphs: list[str] = Field(default_factory=list)
    lists: list[list[str]] = Field(default_factory=list)
    tables: list[StructuredTable] = Field(default_factory=list)
    calculations: list[CalculationBlock] = Field(default_factory=list)

class SectionNode(BaseModel):
    section_id: str
    section_number: str
    title: str
    page_start: int
    page_end: int
    heading_raw: str
    paragraphs: list[str] = Field(default_factory=list)
    lists: list[list[str]] = Field(default_factory=list)
    subsections: list[SubsectionNode] = Field(default_factory=list)
    tables: list[StructuredTable] = Field(default_factory=list)
    calculations: list[CalculationBlock] = Field(default_factory=list)
    notes_and_conditions: list[str] = Field(default_factory=list)

class ExtractedDocument(BaseModel):
    filename: str
    total_pages: int
    full_text: str
    sections: list[SectionNode]
    tables: list[StructuredTable]
    calculations: list[CalculationBlock]
    ocr_needed_pages: list[int] = Field(default_factory=list)
    raw_page_texts: dict[int, str] = Field(default_factory=dict)
