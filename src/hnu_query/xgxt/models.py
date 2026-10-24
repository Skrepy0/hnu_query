from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .dormitory import Dormitory


class Level(str, Enum):
    Undergraduate = "Undergraduate"
    Postgraduate = "Postgraduate"
    Doctoral = "Doctoral"


class Gender(str, Enum):
    Male = "Male"
    Female = "Female"


class PersonalInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    name: str
    enter_year: int
    xz: int | None = None
    stu_id: str
    gender: Gender
    level: Level
    academy: str
    major: str
    class_: str = Field(alias="class")
    dormitory: Dormitory | None = None
    politic: str | None = None
    race: str | None = None
    hometown: str | None = None
    phone: str | None = None
    wechat: str | None = None
    qq: str | None = None
    email: str | None = None
