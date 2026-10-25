from datetime import datetime, timezone
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    # girdiler
    bits: Mapped[int]
    fs_mhz: Mapped[float]
    fin_mhz: Mapped[float]
    amp_dbfs: Mapped[float]
    noise_lsb: Mapped[float]
    hd2_dbc: Mapped[float]
    hd3_dbc: Mapped[float]
    seed: Mapped[int]
    min_enob: Mapped[float]
    # sonuçlar
    snr_db: Mapped[float]
    sinad_db: Mapped[float]
    sfdr_dbc: Mapped[float]
    thd_db: Mapped[float]
    enob: Mapped[float]
    status: Mapped[str] = mapped_column(String(8))