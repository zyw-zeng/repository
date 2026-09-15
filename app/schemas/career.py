"""定义求职材料预览与下载接口的数据结构。"""

from pydantic import BaseModel, Field

from app.schemas.chat import CitationResponse


class CareerMaterialSection(BaseModel):
    """一类岗位定制材料及其可信引用。"""

    title: str
    content: str
    evidence: list[CitationResponse] = Field(default_factory=list)


class CareerMaterialsResponse(BaseModel):
    """围绕当前会话岗位生成的完整求职材料包。"""

    analysis_id: str
    company_name: str | None
    job_title: str
    profile_version: int | None
    score: float
    completeness: float
    feasibility: float
    sections: list[CareerMaterialSection]
