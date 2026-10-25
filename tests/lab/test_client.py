import asyncio
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from hnu_query import lab
from hnu_query.lab._http import BASE_URL


@pytest.mark.parametrize(
    "method,path,fixture,args,verb,params",
    [
        (
            "get_semester",
            "/Common/Common/GetSemDropDownList",
            "GetSemDropDownList.json",
            (),
            "GET",
            {"HasNull": "0"},
        ),
        (
            "get_course_list",
            "/XPK/StudentScoreSearch/GetStudentScoreList",
            "GetStudentScoreList.json",
            ("18&x=1",),
            "POST",
            {
                "page": "1",
                "rows": "15",
                "SemID": "18&x=1",
                "UserID": "202402050201",
            },
        ),
        (
            "get_lab_schedule",
            "/XPK/StuCourseElectiveLook/LoadTableInfo",
            "LoadTableInfo.json",
            (),
            "POST",
            {
                "CourseID": "-999",
                "weeks": "-999",
                "labID": "-999",
                "page": "1",
                "rows": "200",
            },
        ),
    ],
)
@respx.mock
async def test_query_parameters(lab_token, lab_data, method, path, fixture, args, verb, params):
    route = respx.route(method=verb, url=BASE_URL + path).respond(200, json=lab_data(fixture))
    assert await getattr(lab, method)(lab_token, *args)
    request = route.calls.last.request
    assert request.headers["cookie"] == "ASP.NET_SessionId=lab-test"
    if verb == "GET":
        assert dict(request.url.params) == params
    else:
        assert parse_qs(request.content.decode()) == {key: [value] for key, value in params.items()}


@respx.mock
async def test_lab_grade_three_requests(lab_token, lab_data):
    grades = respx.post(BASE_URL + "/XPK/StudentScoreSearch/GetStudentLabScore").respond(
        200, json=lab_data("GetStudentLabScore.json")
    )
    detail = respx.get(BASE_URL + "/XPK/StudentScoreSearch/ShowScore").respond(
        200, json=lab_data("ShowScore.json")
    )
    structure = respx.get(BASE_URL + "/XPK/StudentScoreSearch/GetLabScoreStructure").respond(
        200, json=lab_data("GetLabScoreStructure.json")
    )
    result = await lab.get_lab_grade(lab_token, "68&x=1", "18")
    assert len(result) == 3
    assert parse_qs(grades.calls.last.request.content.decode()) == {
        "page": ["1"],
        "rows": ["15"],
        "SemID": ["18"],
        "CourseID": ["68&x=1"],
        "UserID": [lab_token.stu_id],
    }
    assert dict(detail.calls.last.request.url.params) == {
        "CourseID": "68&x=1",
        "StudentID": lab_token.stu_id,
    }
    assert dict(structure.calls.last.request.url.params) == {"CourseID": "68&x=1"}
    assert all(
        route.calls.last.request.headers["cookie"] == "ASP.NET_SessionId=lab-test"
        for route in (grades, detail, structure)
    )


@respx.mock
async def test_virtual_lab_grade_form(lab_token):
    route = respx.post(BASE_URL + "/XPK/StudentScoreSearch/GetStudentFZLabScore").respond(
        200,
        json={
            "rows": [
                {"LabName": "虚拟实验", "LabScore": "90"},
                {"LabName": "虚拟实验", "LabScore": "80"},
            ]
        },
    )
    result = await lab.get_virtual_lab_grade(lab_token)
    assert len(result) == 1 and result[0].score == "90"
    assert parse_qs(route.calls.last.request.content.decode()) == {
        "page": ["1"],
        "rows": ["15"],
        "SemID": ["0"],
        "CourseID": ["0"],
        "UserID": [lab_token.stu_id],
    }


@pytest.mark.parametrize("status", [302, 403, 500])
@respx.mock
async def test_status_error(lab_token, status):
    respx.get(BASE_URL + "/Common/Common/GetSemDropDownList").respond(status)
    with pytest.raises(lab.LabStatusError) as caught:
        await lab.get_semester(lab_token)
    assert caught.value.status_code == status


@respx.mock
async def test_network_error(lab_token):
    respx.get(BASE_URL + "/Common/Common/GetSemDropDownList").mock(
        side_effect=httpx.ConnectError("offline")
    )
    with pytest.raises(lab.LabNetworkError):
        await lab.get_semester(lab_token)


async def test_client_ownership(lab_token):
    def handler(request):
        assert request.headers["cookie"] == "ASP.NET_SessionId=lab-test"
        assert request.url.host == "10.62.106.112"
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with lab.LabClient(lab_token, client=http) as client:
            assert await client.get_semester() == []
        assert not http.is_closed
    owned = lab.LabClient(lab_token)
    async with owned:
        pass
    assert owned._client.is_closed


@pytest.mark.parametrize("failure", ["http", "cancel"])
async def test_concurrent_requests_cleanup(lab_token, failure):
    started = [asyncio.Event(), asyncio.Event()]
    cancelled = [asyncio.Event(), asyncio.Event()]

    async def handler(request):
        name = request.url.path.rsplit("/", 1)[-1]
        if name == "GetStudentLabScore":
            await asyncio.gather(*(event.wait() for event in started))
            if failure == "cancel":
                raise asyncio.CancelledError()
            return httpx.Response(500)
        index = 0 if name == "ShowScore" else 1
        started[index].set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled[index].set()
            raise

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with lab.LabClient(lab_token, client=http) as client:
            error = lab.LabStatusError if failure == "http" else asyncio.CancelledError
            with pytest.raises(error):
                await asyncio.wait_for(client.get_lab_grade("68", "18"), timeout=2)
        assert all(event.is_set() for event in cancelled)


def test_token_immutable_and_private_cookie():
    headers = {"Cookie": "secret"}
    token = lab.LabToken.from_headers_unchecked(headers, "student")
    headers["Cookie"] = "changed"
    assert token.headers["Cookie"] == "secret"
    assert token.stu_id == "student"
    assert "secret" not in repr(token)
    with pytest.raises(TypeError):
        token.headers["Cookie"] = "changed"
