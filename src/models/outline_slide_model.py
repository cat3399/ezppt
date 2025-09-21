from sqlmodel import JSON, Field, SQLModel


class OutlineSlide(SQLModel, table=True):
    # ===== 复合主键 =====
    project_id: str = Field(
        foreign_key="project.project_id",
        primary_key=True
    )
    slide_id: str = Field(primary_key=True)  # "1.1", "1.2"
    
    # ===== 章节信息=====
    chapter_id: int  # "1", "2", "3"
    chapter_title: str
    
    # ===== 幻灯片信息 =====
    slide_order: int
    slide_topic: str
    slide_content: str
    
    # ===== 生成的内容 =====
    html_content: str = ""
    
    # ===== 视觉建议（JSON）=====
    visual_suggestion: dict = Field(
        default_factory=dict,
        sa_type=JSON
    )
    
    # ===== 图片信息（JSON）=====
    images: dict = Field(
        default_factory=dict,
        sa_type=JSON
    )
    
    # ===== 状态追踪 =====
    status: str = "pending"  # "pending", "generating", "completed", "failed"