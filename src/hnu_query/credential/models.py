from pydantic import BaseModel, Field


class Rank(BaseModel):
    """可信电子凭证中的排名信息。"""

    # 全部课程
    all_gpa: str = Field(description="全部课程的平均学分绩点")
    all_gpa_rank: str = Field(description="全部课程的平均学分绩点排名，格式：1/100")
    all_weighted: str = Field(description="全部课程的加权平均分")
    all_weighted_rank: str = Field(description="全部课程的加权平均分排名")
    all_arithmetic: str = Field(description="全部课程的算术平均分")
    all_arithmetic_rank: str = Field(description="全部课程的算术平均分排名")

    # 必修课（只有值，没有排名）
    must_gpa: str = Field(description="必修课的平均学分绩点")
    must_weighted: str = Field(description="必修课的加权平均分")
    must_arithmetic: str = Field(description="必修课的算术平均分")

    # 核心课程（只有排名）
    core_gpa_rank: str = Field(description="核心课程的平均学分绩点排名")
    core_weighted_rank: str = Field(description="核心课程的加权平均分排名")
    core_arithmetic_rank: str = Field(description="核心课程的算术平均分排名")
