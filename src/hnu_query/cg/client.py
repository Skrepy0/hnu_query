import httpx

from . import parse
from ._http import check_token_expired, redirect_url, request, require_status
from .models import CgAssignment, CgCourse, CgProblem
from .token import CgToken


def _u32(value: int) -> None:
    if type(value) is not int or not 0 <= value < 2**32:
        raise ValueError("CG ID/序号必须为 0 至 4294967295 的整数")


class CgClient:
    """CG 导航和元数据客户端；注入的 HTTP 客户端由调用方关闭。"""

    def __init__(
        self, token: CgToken, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._token = token
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def _get(self, url: str, **kwargs) -> httpx.Response:
        response = await request(
            self._client, "GET", url, headers=dict(self._token.headers), **kwargs
        )
        check_token_expired(response)
        return response

    async def get_course_list(self) -> list[CgCourse] | None:
        response = await self._get("/courselist.jsp")
        if response.status_code == 302:
            main = await self._get("/main.jsp")
            require_status(main)
            return parse.courses_from_main(main.text)
        require_status(response)
        return parse.courses_from_list(response.text)

    async def get_assignment_list(self, course_id: int) -> list[CgAssignment] | None:
        _u32(course_id)
        response = await self._get(
            "/courselist.jsp", params={"courseID": str(course_id)}
        )
        require_status(response, 302)
        context = await self._get(redirect_url(response))
        require_status(context)
        assignments = await self._get("/assignment/mainActiveAssigns.jsp")
        require_status(assignments)
        return parse.assignments(assignments.text)

    async def get_problem_list(self, assign_id: int) -> list[CgProblem] | None:
        _u32(assign_id)
        response = await self._get(
            "/assignment/index.jsp", params={"assignID": str(assign_id)}
        )
        require_status(response)
        return parse.problems(response.text)

    async def get_problem_page(self, assign_id: int, index: int) -> str:
        _u32(assign_id)
        _u32(index)
        response = await self._get(
            "/assignment/programList.jsp",
            params={"proNum": str(index), "assignID": str(assign_id)},
        )
        if response.status_code == 302:
            response = await self._get(redirect_url(response))
        require_status(response)
        return response.text

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "CgClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
