import asyncio

import httpx

from . import parse
from ._http import request
from .models import Course, LabGrade, LabSchedule, Semester, VirtualLabGrade
from .token import LabToken


class LabClient:
    """实验平台异步客户端；注入的 HTTP 客户端由调用方关闭。"""

    def __init__(self, token: LabToken, *, client: httpx.AsyncClient | None = None) -> None:
        self._token = token
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def _text(self, method: str, path: str, **kwargs) -> str:
        response = await request(
            self._client, method, path, headers=dict(self._token.headers), **kwargs
        )
        return response.text

    async def get_semester(self) -> list[Semester]:
        body = await self._text("GET", "/Common/Common/GetSemDropDownList", params={"HasNull": "0"})
        return parse.semester(body)

    async def get_course_list(self, semester_id: str) -> list[Course]:
        body = await self._text(
            "POST",
            "/XPK/StudentScoreSearch/GetStudentScoreList",
            data={
                "page": "1",
                "rows": "15",
                "SemID": semester_id,
                "UserID": self._token.stu_id,
            },
        )
        return parse.course_list(body)

    async def get_lab_schedule(self) -> list[LabSchedule]:
        body = await self._text(
            "POST",
            "/XPK/StuCourseElectiveLook/LoadTableInfo",
            data={
                "CourseID": "-999",
                "weeks": "-999",
                "labID": "-999",
                "page": "1",
                "rows": "200",
            },
        )
        return parse.lab_schedule(body)

    async def get_lab_grade(self, course_id: str, semester_id: str) -> list[LabGrade]:
        tasks = [
            asyncio.create_task(coroutine)
            for coroutine in (
                self._text(
                    "POST",
                    "/XPK/StudentScoreSearch/GetStudentLabScore",
                    data={
                        "page": "1",
                        "rows": "15",
                        "SemID": semester_id,
                        "CourseID": course_id,
                        "UserID": self._token.stu_id,
                    },
                ),
                self._text(
                    "GET",
                    "/XPK/StudentScoreSearch/ShowScore",
                    params={
                        "CourseID": course_id,
                        "StudentID": self._token.stu_id,
                    },
                ),
                self._text(
                    "GET",
                    "/XPK/StudentScoreSearch/GetLabScoreStructure",
                    params={"CourseID": course_id},
                ),
            )
        ]
        try:
            grades, detail, structure = await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        return parse.lab_grade(grades, detail, structure)

    async def get_virtual_lab_grade(self) -> list[VirtualLabGrade]:
        """沿用 Rust 的 SemID/CourseID=0；服务端忽略这两个筛选参数。"""
        body = await self._text(
            "POST",
            "/XPK/StudentScoreSearch/GetStudentFZLabScore",
            data={
                "page": "1",
                "rows": "15",
                "SemID": "0",
                "CourseID": "0",
                "UserID": self._token.stu_id,
            },
        )
        return parse.virtual_lab_grade(body)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "LabClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
