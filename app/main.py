from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional

import pandas as pd
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audio_listener import start_listener
from .db import DoveEvent, get_session, init_db
from .models import DailyStatsOut, DoveEventOut


app = FastAPI(title="DoveListener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Session:
    with get_session() as session:
        yield session


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    start_listener()


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    from pathlib import Path

    static_dir = Path(__file__).parent / "static"
    return FileResponse(static_dir / "index.html")


@app.get("/api/events", response_model=List[DoveEventOut])
def list_events(date_str: Optional[str] = None, db: Session = Depends(get_db)) -> List[DoveEventOut]:
    stmt = select(DoveEvent)
    if date_str:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = datetime.combine(target_date, datetime.min.time())
        end = start + timedelta(days=1)
        stmt = stmt.where(DoveEvent.timestamp >= start, DoveEvent.timestamp < end)

    stmt = stmt.order_by(DoveEvent.timestamp.asc())
    events = db.execute(stmt).scalars().all()
    return [DoveEventOut.model_validate(e) for e in events]


@app.get("/api/stats/today", response_model=DailyStatsOut)
def stats_today(db: Session = Depends(get_db)) -> DailyStatsOut:
    today = date.today()
    return _stats_for_date(today, db)


@app.get("/api/stats/{date_str}", response_model=DailyStatsOut)
def stats_for_date(date_str: str, db: Session = Depends(get_db)) -> DailyStatsOut:
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    return _stats_for_date(target_date, db)


def _stats_for_date(target_date: date, db: Session) -> DailyStatsOut:
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)

    stmt = (
        select(DoveEvent)
        .where(DoveEvent.timestamp >= start_dt, DoveEvent.timestamp < end_dt)
        .order_by(DoveEvent.timestamp.asc())
    )
    events = db.execute(stmt).scalars().all()

    if not events:
        return DailyStatsOut(
            date=target_date.isoformat(),
            total_calls=0,
            first_call_time=None,
            peak_start=None,
            peak_end=None,
            peak_count=0,
            bins=[],
        )

    timestamps = [e.timestamp for e in events]
    df = pd.DataFrame({"timestamp": timestamps})

    first_ts = df["timestamp"].min()
    total_calls = len(df)

    # 以 30 分钟为一个时间桶
    df["bin"] = df["timestamp"].dt.floor("30min")
    grouped = df.groupby("bin").size().reset_index(name="count").sort_values("bin")

    # 找出最高频时间段
    idx_max = grouped["count"].idxmax()
    peak_start_dt = grouped.loc[idx_max, "bin"]
    peak_count = int(grouped.loc[idx_max, "count"])
    peak_end_dt = peak_start_dt + timedelta(minutes=30)

    bins = [
        {
            "start": row["bin"].isoformat(),
            "end": (row["bin"] + timedelta(minutes=30)).isoformat(),
            "count": int(row["count"]),
        }
        for _, row in grouped.iterrows()
    ]

    return DailyStatsOut(
        date=target_date.isoformat(),
        total_calls=total_calls,
        first_call_time=first_ts,
        peak_start=peak_start_dt,
        peak_end=peak_end_dt,
        peak_count=peak_count,
        bins=bins,
    )




