from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import dsp
from .db import Base, SessionLocal, engine
from .models import Run


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="BenchLog API", version="0.1.0", lifespan=lifespan)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RunIn(BaseModel):
    bits: int = Field(14, ge=8, le=18)
    fs_mhz: float = Field(100.0, gt=0)
    fin_mhz: float = Field(10.3, gt=0)
    amp_dbfs: float = Field(-1.0, le=0)
    noise_lsb: float = Field(0.7, ge=0)
    hd2_dbc: float = -85.0
    hd3_dbc: float = -80.0
    seed: int = 1
    min_enob: float = 11.5

    @model_validator(mode="after")
    def fin_below_nyquist(self):
        if self.fin_mhz >= self.fs_mhz / 2:
            raise ValueError("fin_mhz must be below fs_mhz / 2")
        return self


class RunOut(RunIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    snr_db: float
    sinad_db: float
    sfdr_dbc: float
    thd_db: float
    enob: float
    status: str


@app.post("/api/runs", response_model=RunOut, status_code=201)
def create_run(body: RunIn, db: Session = Depends(get_db)):
    params = dsp.CaptureParams(
        bits=body.bits, fs_mhz=body.fs_mhz, fin_mhz=body.fin_mhz,
        amp_dbfs=body.amp_dbfs, noise_lsb=body.noise_lsb,
        hd2_dbc=body.hd2_dbc, hd3_dbc=body.hd3_dbc, seed=body.seed,
    )
    codes, m = dsp.simulate(params)
    result = dsp.analyze(codes, m, body.bits)
    status = "pass" if result["enob"] >= body.min_enob else "fail"

    run = Run(**body.model_dump(), **result, status=status)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@app.get("/api/runs", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db)):
    return db.scalars(select(Run).order_by(Run.id.desc())).all()


@app.get("/api/runs/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return run

@app.get("/api/runs/{run_id}/spectrum")
def get_spectrum(run_id: int, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    params = dsp.CaptureParams(
        bits=run.bits, fs_mhz=run.fs_mhz, fin_mhz=run.fin_mhz,
        amp_dbfs=run.amp_dbfs, noise_lsb=run.noise_lsb,
        hd2_dbc=run.hd2_dbc, hd3_dbc=run.hd3_dbc, seed=run.seed,
    )
    codes, _ = dsp.simulate(params)
    spec = dsp.spectrum_dbfs(codes, run.bits)
    return {
        "fs_mhz": run.fs_mhz,
        "dbfs": [round(float(x), 2) for x in spec],
    }



@app.delete("/api/runs/{run_id}", status_code=204)
def delete_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    db.delete(run)
    db.commit()