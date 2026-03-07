from sqlalchemy import Column, BigInteger, String, Numeric, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    scraped_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    station = Column(String(50), nullable=False)
    fuel_type = Column(String(50), nullable=False)
    price = Column(Numeric(6, 3), nullable=False)
    is_fallback = Column(Boolean, nullable=False, default=False)
