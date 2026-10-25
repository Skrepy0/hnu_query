"""复用 HTTP 连接的异步教务客户端。"""

from collections.abc import Sequence

import httpx

from . import parse
from .exceptions import HdjwNetworkError, HdjwStatusError, TokenExpired
from .models import (
    Course,
    DataSource,
    Display,
    EmptyClassroom,
    ExamSchedule,
    ExtraCourse,
    Grade,
    GradeDetailItem,
    Range,
    Rank,
)
from .token import HdjwToken

BASE_URL = "http://hdjw.hnu.edu.cn"


def semester(xn: int, xq: int) -> str:
    """与 Rust 的 u16 学年、u8 学期参数保持一致。"""
    if type(xn) is not int or not 0 <= xn < 65535:
        raise ValueError("学年必须为 0 至 65534 的整数")
    if type(xq) is not int or not 0 <= xq <= 255:
        raise ValueError("学期必须为 0 至 255 的整数")
    return f"{xn}-{xn + 1}-{xq}"


async def request(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
    try:
        response = await client.request(method, url, follow_redirects=False, **kwargs)
    except httpx.RequestError as exc:
        raise HdjwNetworkError("教务系统网络请求失败") from exc
    if response.status_code >= 400:
        raise HdjwStatusError(response.status_code)
    return response


class HdjwClient:
    """使用 ``async with`` 自动释放连接；注入的 client 由调用者负责关闭。"""

    def __init__(self, token: HdjwToken, *, client: httpx.AsyncClient | None = None) -> None:
        self._token = token
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def _text(self, method: str, path: str, **kwargs) -> str:
        response = await request(
            self._client,
            method,
            BASE_URL + path,
            headers=dict(self._token.headers),
            **kwargs,
        )
        if response.is_redirect:
            location = response.headers.get("location", "").lower()
            if "cas/login" in location or "xk/login" in location or "login.jsp" in location:
                raise TokenExpired("教务会话已过期")
            raise HdjwStatusError(response.status_code, "非预期重定向")
        return response.text

    async def _class_table(self, xn: int, xq: int) -> str:
        return await self._text(
            "GET",
            "/jsxsd/xskb/xskb_list.do",
            params={
                "viweType": "1",
                "needData": "1",
                "pageNum": "1",
                "pageSize": "50",
                "demoStr": "",
                "baseUrl": "/jsxsd",
                "sfykb": "2",
                "xsflMapListJsonStr": "讲课学时,指导学时,实验学时,其他,",
                "zc": "",
                "kbjcmsid": "1",
                "xnxq01id": semester(xn, xq),
            },
        )

    async def get_class_table(self, xn: int, xq: int) -> list[Course]:
        """有课表课程；节次为小节次，周日的 day 为 7。"""
        return parse.class_table(await self._class_table(xn, xq))

    async def get_class_table_extra(self, xn: int, xq: int) -> list[ExtraCourse]:
        """没有排课时间的课程（例如实践课程）。"""
        return parse.class_table_extra(await self._class_table(xn, xq))

    async def get_grade(self, xn: int, xq: int) -> list[Grade]:
        body = await self._text(
            "GET",
            "/jsxsd/kscj/cjcx_list",
            params={
                "pageNum": "1",
                "pageSize": "50",
                "kcxz": "",
                "kcsx": "",
                "kcmc": "",
                "xsfs": "all",
                "sfxsbcxq": "1",
                "kksj": semester(xn, xq),
            },
        )
        return parse.grade(body)

    async def get_grade_detail(self, jx0404id: str) -> list[GradeDetailItem]:
        body = await self._text(
            "GET",
            "/jsxsd/kscj/pscj_list.do",
            params={
                "zcj": "",
                "jx0404id": jx0404id,
            },
        )
        return parse.grade_detail(body)

    async def get_exam_schedule(self, xn: int, xq: int) -> list[ExamSchedule]:
        body = await self._text(
            "GET",
            "/jsxsd/xsks/xsksap_list",
            params={
                "pageNum": "1",
                "pageSize": "20",
                "xqlb": "",
                "xnxqid": semester(xn, xq),
            },
        )
        return parse.exam_schedule(body)

    async def get_rank(
        self,
        selection: Sequence[tuple[int, int]] = (),
        range: Range = Range.Major,
        data_source: DataSource = DataSource.Total,
        display: Display = Display.Max,
    ) -> Rank:
        """selection 为空时查询全部学期；无数据的分类返回 None。"""
        body = await self._text(
            "POST",
            "/jsxsd/xscjsq/cjpmcx_list.do",
            data={
                "xnxq01id": ",".join(semester(xn, xq) for xn, xq in selection),
                "kkxz1": "",
                "pmfs1": "",
                "kclx1": Range(range).value,
                "kcly1": DataSource(data_source).value,
                "xsfs1": Display(display).value,
            },
        )
        return parse.rank(body)

    async def get_empty_classroom(
        self,
        building_id: str,
        week: int,
        day: int,
        time: Sequence[int],
        xn: int,
        xq: int,
    ) -> list[EmptyClassroom]:
        """查询所有所选大节均空闲的教室；大节只支持 1–5。"""
        periods = {1: "0102", 2: "0304", 3: "0506", 4: "0708", 5: "091011"}
        time = list(time)
        if any(type(item) is not int or item not in periods for item in time):
            raise ValueError("空教室查询只支持第 1 至 5 大节")
        if type(day) is not int or not 1 <= day <= 7:
            raise ValueError("星期必须为 1 至 7 的整数")
        if type(week) is not int or not 0 <= week <= 255:
            raise ValueError("周次必须为 0 至 255 的整数")
        body = await self._text(
            "POST",
            "/jsxsd/kbxx/jsjy_query2",
            data={
                "xnxqh": semester(xn, xq),
                "jxlbh": building_id,
                "selectZc": str(week),
                "selectXq": str(day),
                "selectJc": ",".join(periods[item] for item in time),
                "typewhere": "jszq",
            },
        )
        return parse.empty_classroom(body, time)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "HdjwClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
