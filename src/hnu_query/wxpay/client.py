import httpx

from hnu_query.xgxt.dormitory import Dormitory

from .exceptions import WxpayAmbiguityError, WxpayNetworkError, WxpayStatusError
from .parse import convert_dormitory, electricity

QUERY_URL = "http://wxpay.hnu.edu.cn/api/appElectricCharge/checkRoomNo"


class WxpayClient:
    """电量查询客户端，无需 CAS；注入的 HTTP 客户端由调用方关闭。"""

    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def _fetch(self, park: int, building: str, room: str) -> str:
        try:
            response = await self._client.get(
                QUERY_URL,
                follow_redirects=False,
                params={
                    "parkNo": str(park),
                    "buildingNo": building,
                    "rechargeType": "2",
                    "roomNo": room,
                },
                headers={
                    "Referer": "http://wxpay.hnu.edu.cn/electricCharge/home/",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
        except httpx.RequestError as exc:
            raise WxpayNetworkError("宿舍电量网络请求失败") from exc
        if not 200 <= response.status_code < 300:
            raise WxpayStatusError(response.status_code)
        return response.text

    async def get_electricity(self, dormitory: Dormitory) -> str:
        """返回包含单位的原始余额文字；单位可能为度或元。"""
        park, build, room = convert_dormitory(dormitory)
        if build not in ("#2栋", "#3栋"):
            return electricity(await self._fetch(park, build, room))
        # 与 Rust 一样，两次请求都做，且根据请求是否成功选择南北，不根据余额内容猜测。
        buildings = ("52", "53") if build == "#2栋" else ("54", "55")
        responses = []
        for candidate in buildings:
            try:
                responses.append(await self._fetch(park, candidate, room))
            except (WxpayNetworkError, WxpayStatusError):
                pass
        if len(responses) != 1:
            raise WxpayAmbiguityError("无法从南北两次请求中区分宿舍")
        return electricity(responses[0])

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "WxpayClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
