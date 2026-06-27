from fastapi import APIRouter, HTTPException, Query, status

from app.database import get_db_pool
from app.schemas.watchlist import WatchlistCreateRequest, WatchlistEntryResponse

router = APIRouter()


@router.get("", response_model=list[WatchlistEntryResponse])
def list_watchlist(user_id: int = Query(..., description="User ID")):
    pool = get_db_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, source_code, destination_code, journey_date,
                       preferred_class, max_budget, notify_on, is_active, created_at
                FROM watchlist WHERE user_id = %s AND is_active = TRUE
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
    return [
        WatchlistEntryResponse(
            id=r[0], source_code=r[1], destination_code=r[2], journey_date=r[3],
            preferred_class=r[4], max_budget=float(r[5]) if r[5] else None,
            notify_on=r[6] or [], is_active=r[7], created_at=r[8].isoformat(),
        )
        for r in rows
    ]


@router.post("", response_model=WatchlistEntryResponse, status_code=201)
def create_watchlist(body: WatchlistCreateRequest, user_id: int = Query(..., description="User ID")):
    pool = get_db_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO watchlist (user_id, source_code, destination_code, journey_date,
                                       preferred_class, max_budget, notify_on)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, source_code, destination_code, journey_date,
                          preferred_class, max_budget, notify_on, is_active, created_at
                """,
                (user_id, body.source_code.upper(), body.destination_code.upper(),
                 body.journey_date, body.preferred_class, body.max_budget, body.notify_on),
            )
            r = cur.fetchone()
        conn.commit()
    return WatchlistEntryResponse(
        id=r[0], source_code=r[1], destination_code=r[2], journey_date=r[3],
        preferred_class=r[4], max_budget=float(r[5]) if r[5] else None,
        notify_on=r[6] or [], is_active=r[7], created_at=r[8].isoformat(),
    )


@router.delete("/{entry_id}", status_code=204)
def delete_watchlist(entry_id: int, user_id: int = Query(..., description="User ID")):
    pool = get_db_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE watchlist SET is_active = FALSE WHERE id = %s AND user_id = %s RETURNING id",
                (entry_id, user_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
        conn.commit()
