import json

import pytest

from hnu_query.ai import AiParseError, parse


def test_rust_samples(sample):
    tokens = parse.token_list(sample("tokens.json"))
    assert [item.model_dump() for item in tokens] == [{"token_name": "hello", "id": 3296}]
    assert parse.token_key(sample("key.json")) == "zF0Asilc5eRnGbwafZ5gDzIH"
    assert parse.check_action_success(sample("apply-token.json")) is True
    assert parse.remaining_quota(sample("user-info.json")) == 114514


@pytest.mark.parametrize("text", ["{}", '{"data":null}', '{"data":[]}'])
def test_empty_list(text):
    assert parse.token_list(text) == []


def test_duplicate_names_and_u64_limit():
    data = [{"token_name": "same", "id": 0}, {"token_name": "same", "id": 2**64 - 1}]
    assert len(parse.token_list(json.dumps({"data": data}))) == 2


@pytest.mark.parametrize("id", [-1, 2**64, True, "1", 1.0, None])
def test_bad_token_id(id):
    with pytest.raises(AiParseError):
        parse.token_list(json.dumps({"data": [{"token_name": "hello", "id": id}]}))


@pytest.mark.parametrize("data", [False, {}, "", [1], [{"id": 1}], [{"id": 1, "token_name": 2}]])
def test_bad_list(data):
    with pytest.raises(AiParseError):
        parse.token_list(json.dumps({"data": data}))


@pytest.mark.parametrize(
    "parser",
    [
        parse.token_list,
        parse.token_key,
        parse.remaining_quota,
        parse.check_action_success,
        parse.bearer_token,
    ],
)
@pytest.mark.parametrize("text", ["not JSON", "[]", "null", "1"])
def test_invalid_envelope(parser, text):
    with pytest.raises(AiParseError):
        parser(text)


@pytest.mark.parametrize("value", [-1, 2**64, True, "114514", 1.0, None])
def test_bad_quota(value):
    with pytest.raises(AiParseError):
        parse.remaining_quota(json.dumps({"data": {"total_granted": value}}))


@pytest.mark.parametrize("value", [None, 1, "true", [], {}])
def test_action_requires_bool(value):
    with pytest.raises(AiParseError):
        parse.check_action_success(json.dumps({"success": value}))


def test_action_false_and_unmodified_key():
    assert parse.check_action_success('{"success":false}') is False
    assert parse.token_key('{"data":{"key":""}}') == ""
    assert parse.remaining_quota('{"data":{"total_granted":0}}') == 0


@pytest.mark.parametrize("parser", [parse.token_key, parse.remaining_quota, parse.bearer_token])
@pytest.mark.parametrize("text", ["{}", '{"data":null}', '{"data":[]}', '{"data":{}}'])
def test_missing_data_fields(parser, text):
    with pytest.raises(AiParseError):
        parser(text)


@pytest.mark.parametrize("value", [None, 2, "", "a\nb", "a b", "\u4e2d"])
def test_bad_bearer(value):
    with pytest.raises(AiParseError):
        parse.bearer_token(json.dumps({"data": {"token": value}}))


def test_parse_error_does_not_embed_response():
    with pytest.raises(AiParseError) as error:
        parse.token_key('{"secret":"do-not-log"}')
    assert "do-not-log" not in str(error.value)
