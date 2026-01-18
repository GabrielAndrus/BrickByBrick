"""
Solana wallet login + BB Coin API.

- POST /api/solana/verify-wallet  — verify signed message for login
- POST /api/solana/bb-coin/memo-payload  — build memo JSON for LEGO set metadata
- GET  /api/solana/bb-coin/info  — memo program id, BB coin mint
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.solana_bb_coin import (
    build_lego_metadata_json,
    build_memo_payload,
    get_bb_coin_info,
    verify_wallet_signature,
)

router = APIRouter(prefix="/api/solana", tags=["solana", "bb-coin"])


class VerifyWalletRequest(BaseModel):
    message: str
    signature: str
    publicKey: str


class VerifyWalletResponse(BaseModel):
    verified: bool


class MemoPayloadRequest(BaseModel):
    projectName: str
    buildId: str
    pieceCount: dict  # { total_pieces, breakdown, estimated_cost }
    stepCount: int


class MemoPayloadResponse(BaseModel):
    memoPayload: str
    metadata: dict


@router.post("/verify-wallet", response_model=VerifyWalletResponse)
def verify_wallet(req: VerifyWalletRequest) -> VerifyWalletResponse:
    """Verify a message signed by the user's Solana wallet (e.g. Phantom). Use for login."""
    ok = verify_wallet_signature(req.message, req.signature, req.publicKey)
    return VerifyWalletResponse(verified=ok)


@router.post("/bb-coin/memo-payload", response_model=MemoPayloadResponse)
def bb_coin_memo_payload(req: MemoPayloadRequest) -> MemoPayloadResponse:
    """Build the memo payload string for sending the user's current LEGO set to BB Coin."""
    pc = req.pieceCount or {}
    breakdown = pc.get("breakdown") or []
    total = int(pc.get("total_pieces") or 0)
    cost = float(pc.get("estimated_cost") or 0)
    metadata = build_lego_metadata_json(
        project_name=req.projectName,
        build_id=req.buildId,
        total_pieces=total,
        step_count=req.stepCount,
        breakdown=breakdown,
        estimated_cost=cost,
    )
    payload = build_memo_payload(metadata)
    return MemoPayloadResponse(memoPayload=payload, metadata=metadata)


@router.get("/bb-coin/info")
def bb_coin_info() -> dict:
    """Return Memo program id and BB Coin mint for the frontend."""
    return get_bb_coin_info()
