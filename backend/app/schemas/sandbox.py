import uuid

from pydantic import BaseModel


class CatalogBusiness(BaseModel):
    place_id: str
    name: str
    business_type: str
    address: str | None
    review_count: int
    imported: bool
    business_id: uuid.UUID | None = None


class CatalogScenario(BaseModel):
    id: str
    description: str
    main: CatalogBusiness
    competitors: list[CatalogBusiness]


class CatalogResponse(BaseModel):
    scenarios: list[CatalogScenario]
    standalone: list[CatalogBusiness]


class SandboxImport(BaseModel):
    place_id: str
    as_competitor_for: uuid.UUID | None = None


class SandboxResetResponse(BaseModel):
    deleted: int
