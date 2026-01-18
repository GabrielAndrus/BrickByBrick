"""
Solana + BB Coin integration.

- Wallet login: verify Ed25519 signature from Solana wallet (e.g. Phantom).
- BB Coin: build LEGO set metadata for on-chain Memo. The BB coin is our minted token;
  we send the user's current LEGO set metadata via a Memo instruction (fits in a tx).
"""

import json
import os
from typing import Any

import base58
from nacl.encoding import RawEncoder
from nacl.signing import VerifyKey

# Memo program (official): any tx can attach a memo with data
MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"

# BB Coin mint address (set via env; use devnet mint when available)
BB_COIN_MINT = os.getenv("BB_COIN_MINT_ADDRESS", "")

# Max memo size to stay under Solana tx limit (~1232 bytes total; memo ~600 safe)
MAX_MEMO_BYTES = 600


def build_lego_metadata_json(
    project_name: str,
    build_id: str,
    total_pieces: int,
    step_count: int,
    breakdown: list[dict[str, Any]],
    estimated_cost: float = 0,
) -> dict[str, Any]:
    """Build a compact JSON object for BB Coin memo (user's current LEGO set)."""
    # Compact keys to save bytes
    b = [{"id": x.get("part_id"), "q": x.get("quantity", 0)} for x in (breakdown or [])[:20]]
    return {
        "t": "BB",  # type: BB Coin
        "n": (project_name or "My Dorm Room")[:80],
        "i": (build_id or "")[:64],
        "p": total_pieces,
        "s": step_count,
        "c": estimated_cost,
        "b": b,
        "ts": int(__import__("time").time()),
    }


def build_memo_payload(metadata: dict[str, Any]) -> str:
    """Serialize metadata to a JSON string for Memo instruction. Truncate if too large."""
    s = json.dumps(metadata, separators=(",", ":"))
    buf = s.encode("utf-8")
    if len(buf) > MAX_MEMO_BYTES:
        # Drop breakdown and shorten name to fit
        m2 = {k: v for k, v in metadata.items() if k != "b"}
        m2["n"] = (m2.get("n") or "")[:40]
        s = json.dumps(m2, separators=(",", ":"))
    return s


def verify_wallet_signature(message: str, signature_b58: str, public_key_b58: str) -> bool:
    """
    Verify an Ed25519 signature from a Solana wallet (e.g. Phantom).

    - message: raw string the user signed (must match exactly what was passed to signMessage).
    - signature_b58: base58-encoded signature (64 bytes when decoded).
    - public_key_b58: base58-encoded Ed25519 public key (32 bytes when decoded).
    """
    try:
        sig = base58.b58decode(signature_b58)
        pk = base58.b58decode(public_key_b58)
    except Exception:
        return False
    if len(pk) != 32 or len(sig) != 64:
        return False
    msg_bytes = message.encode("utf-8")
    try:
        vk = VerifyKey(pk, encoder=RawEncoder)
        vk.verify(msg_bytes, sig, encoder=RawEncoder)  # detached: (message, signature)
        return True
    except Exception:
        return False


def get_bb_coin_info() -> dict[str, str]:
    """Return BB Coin and Memo program ids for the frontend."""
    return {
        "memoProgramId": MEMO_PROGRAM_ID,
        "bbCoinMint": BB_COIN_MINT or "",
    }
