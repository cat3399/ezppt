from datetime import datetime
from pydantic import BaseModel
from sqlmodel import SQLModel, Field

class Status():
    pending = "pending"
    generating = "generating"
    completed = "completed"
    failed = "failed"


class Project(SQLModel, table=True):
    project_id: str = Field(primary_key=True)
    project_name: str
    status: str
    create_time: datetime
    topic: str
    audience: str = "大众"
    style: str = "简洁明了"
    page_num: int = 10
    pdf_status: str = Status.pending
    pptx_status: str = Status.pending

class ProjectIn(BaseModel):
    topic: str = Field(..., min_length=1, max_length=1000)
    audience: str = Field(default="大众", max_length=50)
    style: str = Field(default="简洁明了", max_length=50)
    page_num: int = Field(default=10, ge=1, le=100)
    reference_content: str = Field(default="")

