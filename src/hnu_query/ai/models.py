from pydantic import BaseModel, ConfigDict, Field


class TokenInfo(BaseModel):
    """API Token 元数据；名称可以重复，操作时应使用 ID。"""

    model_config = ConfigDict(strict=True)

    token_name: str
    id: int = Field(ge=0, lt=2**64)
