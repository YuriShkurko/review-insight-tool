import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.competitor_link import CompetitorLink


class Business(Base):
    __tablename__ = "businesses"
    __table_args__ = (UniqueConstraint("user_id", "place_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    place_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_maps_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # optional; not in API yet
    avg_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    is_competitor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="businesses")
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    analysis: Mapped["Analysis | None"] = relationship(
        back_populates="business", uselist=False, cascade="all, delete-orphan"
    )
    competitor_links_out: Mapped[list["CompetitorLink"]] = relationship(
        CompetitorLink,
        foreign_keys=[CompetitorLink.target_business_id],
        back_populates="target_business",
        cascade="all, delete-orphan",
    )
    competitor_links_in: Mapped[list["CompetitorLink"]] = relationship(
        CompetitorLink,
        foreign_keys=[CompetitorLink.competitor_business_id],
        back_populates="competitor_business",
    )
