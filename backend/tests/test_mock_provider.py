"""Tests for the mock review provider."""

from app.mock.reviews import generate_mock_reviews
from app.providers.mock_provider import MockProvider


class TestMockReviewGeneration:
    def test_returns_expected_count(self, sample_place_id: str):
        reviews = generate_mock_reviews(sample_place_id, count=10)
        assert len(reviews) == 10

    def test_default_count_is_15(self, sample_place_id: str):
        reviews = generate_mock_reviews(sample_place_id)
        assert len(reviews) == 15

    def test_deterministic_output(self, sample_place_id: str):
        first = generate_mock_reviews(sample_place_id)
        second = generate_mock_reviews(sample_place_id)
        assert first == second

    def test_different_place_ids_produce_different_reviews(self):
        a = generate_mock_reviews("place_a")
        b = generate_mock_reviews("place_b")
        ids_a = {r["external_id"] for r in a}
        ids_b = {r["external_id"] for r in b}
        assert ids_a != ids_b

    def test_review_shape(self, sample_place_id: str):
        reviews = generate_mock_reviews(sample_place_id, count=1)
        r = reviews[0]
        assert "external_id" in r
        assert "source" in r
        assert "author" in r
        assert "rating" in r
        assert "text" in r
        assert "published_at" in r

    def test_external_id_prefix(self, sample_place_id: str):
        reviews = generate_mock_reviews(sample_place_id, count=3)
        for r in reviews:
            assert r["external_id"].startswith("mock_")

    def test_source_is_mock(self, sample_place_id: str):
        reviews = generate_mock_reviews(sample_place_id, count=3)
        for r in reviews:
            assert r["source"] == "mock"

    def test_ratings_in_valid_range(self, sample_place_id: str):
        reviews = generate_mock_reviews(sample_place_id)
        for r in reviews:
            assert 1 <= r["rating"] <= 5


class TestMockProvider:
    def test_implements_provider_interface(self):
        provider = MockProvider()
        reviews = provider.fetch_reviews("test_place")
        assert isinstance(reviews, list)
        assert len(reviews) > 0

    def test_ignores_google_maps_url(self, sample_place_id: str):
        provider = MockProvider()
        with_url = provider.fetch_reviews(sample_place_id, "https://maps.google.com/...")
        without_url = provider.fetch_reviews(sample_place_id)
        assert with_url == without_url
