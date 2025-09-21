from sqlmodel import SQLModel, Field, JSON

class Outline(SQLModel, table=True):
    # 主键 = 外键
    project_id: str = Field(
        foreign_key="project.project_id", 
        primary_key=True
    )
    
    # 基本信息（从 project 冗余过来，方便查询）
    topic: str
    audience: str = "大众"
    style: str = "简洁明了"
    page_num: int = 10
    
    # Outline 级别的数据
    global_visual_suggestion: dict = Field(default_factory=dict, sa_type=JSON)
    outline_json: dict = Field(default_factory=dict, sa_type=JSON)
    images: dict = Field(default_factory=dict, sa_type=JSON)
    # 参考资料
    reference_content: str = ""
    # 状态
    # status: str = "pending"  # "generating", "completed"
