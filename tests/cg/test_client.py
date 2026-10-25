import httpx
import pytest
import respx

from hnu_query import cg
from hnu_query.cg._http import BASE_URL


@respx.mock
async def test_multi_course_page(cg_token, cg_text):
    route = respx.get(BASE_URL + "/courselist.jsp").respond(200, text=cg_text("courselist.html"))
    result = await cg.get_course_list(cg_token)
    assert [c.id for c in result] == [1001, 2002, 3003]
    assert route.calls.last.request.headers["cookie"] == "JSESSIONID=cg-test"
    assert len(respx.calls) == 1


@respx.mock
async def test_single_course_main_branch(cg_token, cg_text):
    respx.get(BASE_URL + "/courselist.jsp").respond(302, headers={"location": "/main.jsp"})
    respx.get(BASE_URL + "/main.jsp").respond(200, text=cg_text("main_single_course.html"))
    result = await cg.get_course_list(cg_token)
    assert [(c.id, c.name) for c in result] == [(1001, "高等数学")]
    assert len(respx.calls) == 2


@pytest.mark.parametrize("location", ["main.jsp", "/main.jsp", BASE_URL + "/main.jsp"])
@respx.mock
async def test_course_context_before_assignments(cg_token, cg_text, location):
    context = respx.get(BASE_URL + "/courselist.jsp", params={"courseID": "1001"}).respond(
        302, headers={"location": location}
    )
    main = respx.get(BASE_URL + "/main.jsp").respond(200, text="context ready")
    assignments = respx.get(BASE_URL + "/assignment/mainActiveAssigns.jsp").respond(
        200, text=cg_text("assignment_list.html")
    )
    result = await cg.get_assignment_list(cg_token, 1001)
    assert [a.id for a in result] == [5001, 5002, 5003]
    assert [call.request.url.path for call in respx.calls] == [
        "/courselist.jsp",
        "/main.jsp",
        "/assignment/mainActiveAssigns.jsp",
    ]
    assert all(
        route.calls.last.request.headers["cookie"] == "JSESSIONID=cg-test"
        for route in (context, main, assignments)
    )


@respx.mock
async def test_problem_list_params(cg_token, cg_text):
    route = respx.get(BASE_URL + "/assignment/index.jsp").respond(
        200, text=cg_text("problem_list.html")
    )
    result = await cg.get_problem_list(cg_token, 5001)
    assert len(result) == 3
    assert dict(route.calls.last.request.url.params) == {"assignID": "5001"}


@pytest.mark.parametrize(
    "location",
    [
        "programList_ce.jsp?problemID=20001",
        "/assignment/programList_ce.jsp?problemID=20001",
        BASE_URL + "/assignment/programList_ce.jsp?problemID=20001",
    ],
)
@respx.mock
async def test_problem_page_redirect(cg_token, cg_text, location):
    first = respx.get(BASE_URL + "/assignment/programList.jsp").respond(
        302, headers={"location": location}
    )
    final = respx.get(BASE_URL + "/assignment/programList_ce.jsp?problemID=20001").respond(
        200, text=cg_text("problem_page.html")
    )
    html = await cg.get_problem_page(cg_token, 5001, 1)
    assert html == cg_text("problem_page.html")
    assert dict(first.calls.last.request.url.params) == {
        "proNum": "1",
        "assignID": "5001",
    }
    assert final.calls.last.request.headers["cookie"] == "JSESSIONID=cg-test"
    assert len(respx.calls) == 2


@respx.mock
async def test_direct_problem_page_does_not_refetch_without_parameters(cg_token, cg_text):
    route = respx.get(BASE_URL + "/assignment/programList.jsp").respond(
        200, text=cg_text("problem_page.html")
    )
    html = await cg.get_problem_page(cg_token, 5001, 1)
    assert html == cg_text("problem_page.html")
    assert route.call_count == 1


@pytest.mark.parametrize(
    "method,path,args",
    [
        ("get_course_list", "/courselist.jsp", ()),
        ("get_assignment_list", "/courselist.jsp", (1001,)),
        ("get_problem_list", "/assignment/index.jsp", (5001,)),
        ("get_problem_page", "/assignment/programList.jsp", (5001, 1)),
    ],
)
@respx.mock
async def test_expired_initial_page(cg_token, method, path, args):
    respx.get(BASE_URL + path).respond(302, headers={"location": "/indexcs/simple.jsp?loginErr=0"})
    with pytest.raises(cg.TokenExpired):
        await getattr(cg, method)(cg_token, *args)
    assert len(respx.calls) == 1


@respx.mock
async def test_expired_followed_problem_page(cg_token):
    respx.get(BASE_URL + "/assignment/programList.jsp").respond(
        302, headers={"location": "programList_ce.jsp"}
    )
    respx.get(BASE_URL + "/assignment/programList_ce.jsp").respond(
        302, headers={"location": "/login/expired"}
    )
    with pytest.raises(cg.TokenExpired):
        await cg.get_problem_page(cg_token, 1, 1)


@respx.mock
async def test_expired_course_context_stops_assignment_query(cg_token):
    respx.get(BASE_URL + "/courselist.jsp").respond(302, headers={"location": "/main.jsp"})
    respx.get(BASE_URL + "/main.jsp").respond(302, headers={"location": "/indexcs/simple.jsp"})
    with pytest.raises(cg.TokenExpired):
        await cg.get_assignment_list(cg_token, 1001)
    assert len(respx.calls) == 2


@pytest.mark.parametrize(
    "location,error",
    [
        (None, cg.CgNavigationError),
        ("https://example.org/page", cg.CgNavigationError),
        ("//example.org/page", cg.CgNavigationError),
        ("https://cg.hnu.edu.cn:bad/page", cg.CgNetworkError),
    ],
)
@respx.mock
async def test_invalid_redirect(cg_token, location, error):
    respx.get(BASE_URL + "/assignment/programList.jsp").respond(
        302, headers={"location": location} if location is not None else {}
    )
    with pytest.raises(error):
        await cg.get_problem_page(cg_token, 1, 1)
    assert len(respx.calls) == 1


@pytest.mark.parametrize("status", [303, 403, 500])
@respx.mock
async def test_http_errors(cg_token, status):
    respx.get(BASE_URL + "/courselist.jsp").respond(status)
    with pytest.raises(cg.CgStatusError) as caught:
        await cg.get_course_list(cg_token)
    assert caught.value.status_code == status


@respx.mock
async def test_network_error(cg_token):
    respx.get(BASE_URL + "/courselist.jsp").mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(cg.CgNetworkError):
        await cg.get_course_list(cg_token)


@pytest.mark.parametrize("value", [-1, True, 2**32, "1"])
async def test_invalid_u32_before_request(cg_token, value):
    async with cg.CgClient(cg_token) as client:
        with pytest.raises(ValueError):
            await client.get_assignment_list(value)
        with pytest.raises(ValueError):
            await client.get_problem_list(value)
        with pytest.raises(ValueError):
            await client.get_problem_page(1, value)


async def test_connection_ownership(cg_token):
    def handler(request):
        assert request.headers["cookie"] == "JSESSIONID=cg-test"
        return httpx.Response(200, text="<html>没有课程</html>")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with cg.CgClient(cg_token, client=http) as client:
            assert await client.get_course_list() is None
        assert not http.is_closed
    owned = cg.CgClient(cg_token)
    async with owned:
        pass
    assert owned._client.is_closed


def test_token_immutable_and_private():
    headers = {"Cookie": "secret"}
    token = cg.CgToken.from_headers_unchecked(headers)
    headers["Cookie"] = "changed"
    assert token.headers["Cookie"] == "secret"
    assert "secret" not in repr(token)
    with pytest.raises(TypeError):
        token.headers["Cookie"] = "changed"
