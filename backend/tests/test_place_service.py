"""Unit tests for place_service URL parsing and place ID extraction."""

from app.services.place_service import parse_place_id_from_url


class TestParsePlaceIdFromUrl:
    """Test parse_place_id_from_url against supported Google Maps URL formats."""

    def test_place_id_query_param(self):
        url = "https://www.google.com/maps?place_id=ChIJwS1PVYVLHRURO1XNXZw12AA"
        assert parse_place_id_from_url(url) == "ChIJwS1PVYVLHRURO1XNXZw12AA"

    def test_place_id_with_other_params(self):
        url = "https://www.google.com/maps?foo=bar&place_id=ChIJN1t_tDeuEmsRUsoyG83frY4&utm_source=share"
        assert parse_place_id_from_url(url) == "ChIJN1t_tDeuEmsRUsoyG83frY4"

    def test_query_place_id_param(self):
        url = "https://www.google.com/maps/search/?api=1&query_place_id=ChIJwS1PVYVLHRURO1XNXZw12AA"
        assert parse_place_id_from_url(url) == "ChIJwS1PVYVLHRURO1XNXZw12AA"

    def test_place_id_legacy_colon(self):
        url = "https://example.com/maps?place_id:ChIJtest123"
        assert parse_place_id_from_url(url) == "ChIJtest123"

    def test_place_slash_data_hex_format(self):
        url = (
            "https://www.google.com/maps/place/Test+Business/"
            "@32.071,34.788,14z/data=!4m2!3m1!1s0x151d4b85554f2dc1:0xd8359c5dcd553b"
        )
        assert parse_place_id_from_url(url) == "0x151d4b85554f2dc1:0xd8359c5dcd553b"

    def test_place_slash_data_chij_format(self):
        url = (
            "https://www.google.com/maps/place/Lager+%26+Ale/"
            "@32.071,34.788,14z/data=!4m6!3m5!1sChIJwS1PVYVLHRURO1XNXZw12AA!8m2!3d32.071!4d34.788"
        )
        assert parse_place_id_from_url(url) == "ChIJwS1PVYVLHRURO1XNXZw12AA"

    def test_integration_sample_url_hex(self):
        url = (
            "https://www.google.com/maps/place/Test+Business/"
            "@0,0,17z/data=!4m2!3m1!1s0x0:0x1"
        )
        assert parse_place_id_from_url(url) == "0x0:0x1"

    def test_bare_1s_chij(self):
        url = "https://www.google.com/maps?data=!3m1!4b1!4m2!3m1!1sChIJwS1PVYVLHRURO1XNXZw12AA"
        assert parse_place_id_from_url(url) == "ChIJwS1PVYVLHRURO1XNXZw12AA"

    def test_bare_1s_hex(self):
        url = "https://www.google.com/maps?data=!1s0x151d4b85554f2dc1:0xd8359c5dcd553b"
        assert parse_place_id_from_url(url) == "0x151d4b85554f2dc1:0xd8359c5dcd553b"

    def test_whitespace_stripped(self):
        url = "  https://www.google.com/maps?place_id=ChIJwS1PVYVLHRURO1XNXZw12AA  "
        assert parse_place_id_from_url(url) == "ChIJwS1PVYVLHRURO1XNXZw12AA"

    def test_fragment_ignored(self):
        url = "https://www.google.com/maps?place_id=ChIJwS1PVYVLHRURO1XNXZw12AA#reviews"
        assert parse_place_id_from_url(url) == "ChIJwS1PVYVLHRURO1XNXZw12AA"

    def test_url_encoded_place_id_param(self):
        url = "https://www.google.com/maps?place_id%3DChIJwS1PVYVLHRURO1XNXZw12AA"
        assert parse_place_id_from_url(url) == "ChIJwS1PVYVLHRURO1XNXZw12AA"

    def test_google_maps_place_with_tracking(self):
        url = (
            "https://www.google.com/maps/place/Cafe+Test/@32.0,34.0,17z/"
            "data=!3m1!4b1!4m6!3m5!1sChIJabc123!8m2!3d32!4d34?entry=ttu&g_ep=xyz"
        )
        assert parse_place_id_from_url(url) == "ChIJabc123"

    def test_empty_string_returns_none(self):
        assert parse_place_id_from_url("") is None

    def test_none_like_returns_none(self):
        assert parse_place_id_from_url("   ") is None

    def test_search_only_no_place_id_returns_none(self):
        url = "https://www.google.com/maps/search/?api=1&query=coffee+shop+tel+aviv"
        assert parse_place_id_from_url(url) is None

    def test_plain_search_q_param_returns_none(self):
        url = "https://www.google.com/maps?q=32.071,34.788"
        assert parse_place_id_from_url(url) is None

    def test_random_url_returns_none(self):
        url = "https://example.com/not-maps"
        assert parse_place_id_from_url(url) is None
