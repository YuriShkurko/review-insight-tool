import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CompetitorLink(Base):
    __tablename__ = "competitor_links"
    __table_args__ = (UniqueConstraint("target_business_id", "competitor_business_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    target_business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    competitor_business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    target_business: Mapped["Business"] = relationship(
        "Business",
        foreign_keys=[target_business_id],
        back_populates="competitor_links_out",
    )
    competitor_business: Mapped["Business"] = relationship(
        "Business",
        foreign_keys=[competitor_business_id],
        back_populates="competitor_links_in",
    )
