from pydantic import BaseModel


class CgCourse(BaseModel):
    id: int
    name: str


class CgAssignment(BaseModel):
    id: int
    name: str


class CgProblem(BaseModel):
    index: int
    id: int
    title: str
    score: float
