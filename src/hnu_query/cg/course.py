from .client import CgClient
from .models import CgAssignment, CgCourse, CgProblem
from .token import CgToken

__all__ = [
    "CgAssignment",
    "CgCourse",
    "CgProblem",
    "get_assignment_list",
    "get_course_list",
    "get_problem_list",
    "get_problem_page",
]


async def get_course_list(token: CgToken) -> list[CgCourse] | None:
    async with CgClient(token) as client:
        return await client.get_course_list()


async def get_assignment_list(token: CgToken, course_id: int) -> list[CgAssignment] | None:
    async with CgClient(token) as client:
        return await client.get_assignment_list(course_id)


async def get_problem_list(token: CgToken, assign_id: int) -> list[CgProblem] | None:
    async with CgClient(token) as client:
        return await client.get_problem_list(assign_id)


async def get_problem_page(token: CgToken, assign_id: int, index: int) -> str:
    async with CgClient(token) as client:
        return await client.get_problem_page(assign_id, index)
