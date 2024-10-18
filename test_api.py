from app.v2.api.utils import get_request


def test_get_request():
    data = get_request("/do_you_spain/limit=5")
    print(data)


test_get_request()
