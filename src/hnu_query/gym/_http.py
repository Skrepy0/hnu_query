import httpx

from .exceptions import GymNetworkError, GymStatusError

BASE_URL = "http://gymos.hnu.edu.cn/bdlp_api_fitness_test_student_h5"
API_URL = BASE_URL + "/public/index.php/index"


async def request(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
    try:
        response = await client.request(method, url, follow_redirects=False, **kwargs)
    except httpx.RequestError as exc:
        raise GymNetworkError("体测系统网络请求失败") from exc
    if not 200 <= response.status_code < 300:
        raise GymStatusError(response.status_code)
    return response
