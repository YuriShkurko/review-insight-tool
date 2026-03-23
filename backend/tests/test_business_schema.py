"""Tests for business schema validation."""

from app.schemas.business import BusinessCreate, BusinessType


class TestBusinessType:
    def test_all_types_exist(self):
        expected = {
            "restaurant",
            "bar",
            "cafe",
            "gym",
            "salon",
            "hotel",
            "clinic",
            "retail",
            "other",
        }
        actual = {t.value for t in BusinessType}
        assert actual == expected

    def test_default_type_is_other(self):
        payload = BusinessCreate(google_maps_url="https://maps.google.com/place/Test")
        assert payload.business_type == BusinessType.other

    def test_explicit_type(self):
        payload = BusinessCreate(
            google_maps_url="https://maps.google.com/place/Test",
            business_type="restaurant",
        )
        assert payload.business_type == BusinessType.restaurant

    def test_place_id_only(self):
        payload = BusinessCreate(place_id="ChIJtest123")
        assert payload.place_id == "ChIJtest123"
        assert payload.google_maps_url is None
