import asyncio

import httpx

from . import parse
from ._http import API_URL, request
from .models import Appointment, Grade
from .token import GymToken


class GymClient:
    """复用连接的异步客户端；调用方注入的 HTTP 客户端由调用方关闭。"""

    def __init__(self, token: GymToken, *, client: httpx.AsyncClient | None = None) -> None:
        self._token = token
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def _text(self, path: str, **kwargs) -> str:
        response = await request(
            self._client,
            "POST",
            API_URL + path,
            headers=dict(self._token.headers),
            **kwargs,
        )
        return response.text

    async def get_appointment(self) -> list[Appointment]:
        """查询预约列表，并逐项取得预约描述与体测类型。"""
        rows = parse.appointment_list(await self._text("/Appoint/getStudentClass"))
        result = []
        for row in rows:
            detail = await self._text(
                "/Appoint/getSchoolFitClassDetail",
                data={
                    "class_id": str(row.class_id),
                    "class_time": row.class_time,
                    "test_time": row.test_time,
                },
            )
            result.append(parse.appointment_item(row, detail))
        return result

    async def get_grade(self, xn: int) -> Grade:
        """按学年查询，合并成绩摘要与视力/分数详情。"""
        if type(xn) is not int or not 0 <= xn <= 65535:
            raise ValueError("学年必须为 0 至 65535 的整数")
        tasks = [
            asyncio.create_task(self._text(path, data={"year_num": str(xn)}))
            for path in (
                "/Report/getStudentScore",
                "/Report/getEyeDetails",
            )
        ]
        try:
            summary, detail = await asyncio.gather(*tasks)
        except BaseException:
            # 与 Rust try_join 一样，任一请求失败时结束另一个请求再释放连接。
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        return parse.grade(summary, detail)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "GymClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
