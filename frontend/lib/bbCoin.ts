/**
 * BB Coin — send the user's current LEGO set metadata on Solana via Memo.
 *
 * Uses the Memo program so we don't need a custom program. The memo payload
 * is a compact JSON describing the LEGO set (project, pieces, steps, etc.).
 */

import { PublicKey, Transaction, TransactionInstruction } from '@solana/web3.js'

const MEMO_PROGRAM_ID = new PublicKey('MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr')

const MAX_MEMO_BYTES = 600

export interface LegoMetadataInput {
  projectName: string
  buildId: string
  totalPieces: number
  stepCount: number
  estimatedCost?: number
  breakdown?: Array<{ part_id: string; quantity: number }>
}

/**
 * Build a compact metadata object for the BB Coin memo (fits in tx size limit).
 */
export function buildBbCoinMetadata(input: LegoMetadataInput): Record<string, unknown> {
  const b = (input.breakdown || [])
    .slice(0, 20)
    .map((x) => ({ id: x.part_id, q: x.quantity }))
  return {
    t: 'BB',
    n: (input.projectName || 'My Dorm Room').slice(0, 80),
    i: (input.buildId || '').slice(0, 64),
    p: input.totalPieces,
    s: input.stepCount,
    c: input.estimatedCost ?? 0,
    b,
    ts: Math.floor(Date.now() / 1000),
  }
}

function buildMemoPayload(metadata: Record<string, unknown>): string {
  let s = JSON.stringify(metadata)
  if (Buffer.byteLength(s, 'utf8') > MAX_MEMO_BYTES) {
    const m2 = { ...metadata, b: undefined, n: (metadata.n as string)?.slice(0, 40) }
    s = JSON.stringify(m2)
  }
  return s
}

/**
 * Build a Solana Transaction containing a single Memo instruction with the LEGO set metadata.
 * The wallet will sign and send this; the memo is permanently stored on-chain.
 */
export function buildMemoTransaction(metadata: LegoMetadataInput): {
  transaction: Transaction
  memoPayload: string
} {
  const obj = buildBbCoinMetadata(metadata)
  const memoPayload = buildMemoPayload(obj)
  const ix = new TransactionInstruction({
    programId: MEMO_PROGRAM_ID,
    keys: [],
    data: Buffer.from(memoPayload, 'utf8'),
  })
  const transaction = new Transaction().add(ix)
  return { transaction, memoPayload }
}
