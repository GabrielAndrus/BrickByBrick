# Brick By Brick — Reality-to-Brick

Submitted to UofT Hacks 13: https://devpost.com/software/lego-6928rf?ref_content=user-portfolio&ref_feature=in_progress

> Transform your space into buildable LEGO sets. Upload a video of your room or objects, and get LEGO instructions, piece counts, and 3D previews — with optional Solana BB Coins to record your builds on-chain.

---

## Overview

**Brick By Brick** is a full-stack application that turns videos  objects into LEGO building plans. It combines:

- **Video → 3D**: Upload a 360° video; the app processes it and shows an interactive 3D dorm room (or scene) in 3JS.
- **LEGO pipeline**: Voxel-based geometry is converted into a LEGO manifest (bricks, colors, positions) using a greedy fitting algorithm, with optional AI enhancement for instructions.
- **Instruction manuals**: Step-by-step, LEGO-style instructions with piece counts, baseplate selection, and PDF download.
- **BB Coins**: Login with a Solana wallet and save build metadata on-chain via Memo instructions + keep track of your lego creations.

---

## Tech Stack

### Frontend

- **Next.js 16** (App Router), **React 19**, **TypeScript**
- **Three.js**, **@react-three/fiber**, **@react-three/drei** — 3D scenes and LEGO-style rendering
- **Tailwind CSS**, **Framer Motion** — layout and animations
- **@google/generative-ai** (Gemini) — instruction enhancement, video→Three.js, model analysis
- **Solana** — `@solana/web3.js`, `@solana/wallet-adapter-*` (Phantom, Solflare)
- **jsPDF**, **html2canvas** — PDF instruction generation
- **@lottiefiles/dotlottie-react** — loading animation

### Backend

- **FastAPI**, **uvicorn**, **Pydantic**
- **Twelve Labs** — video indexing and scene/object analysis
- **Google Gemini** — used via Backboard or directly where integrated
- **Master Builder** — greedy LEGO fitting from voxels (Rebrickable, part discovery, vector DB)
- **Backboard** (optional) — AI/memory layer for LEGO build orchestration
- **Solana** — `solana`, `solders`, `pynacl`, `base58` for Memo and wallet verification
- **NumPy, OpenCV, SciPy, Pillow** — voxelization and image processing

---

## Project Structure

```
uoft/
├── frontend/                 # Next.js app
│   ├── app/
│   │   ├── page.tsx          # Main UI: upload, 3D, Full Set, InstructionBook, BB Coins
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   └── components/
│   │       ├── InstructionBook.tsx    # LEGO instruction book + PDF
│   │       ├── InstructionManual.tsx
│   │       ├── ModelDetailsDisplay.tsx
│   │       ├── ModelSelector.tsx
│   │       └── SolanaWalletProvider.tsx
│   ├── lib/
│   │   ├── legoManualGenerator.ts     # Piece counting, instruction generation, baseplate
│   │   ├── legoThreeJSBuilder.ts      # Manifest → Three.js LEGO scene
│   │   ├── legoPDFGenerator.ts        # LEGO-style PDF
│   │   ├── geminiLegoInstructions.ts  # Gemini-enhanced instructions
│   │   ├── geminiLegoConverter.ts
│   │   ├── videoToThreeJS.ts          # Video → Three.js (Gemini)
│   │   ├── threeJSToLegoPieces.ts     # Three.js → piece analysis
│   │   ├── bbCoin.ts                  # Solana Memo + LEGO metadata
│   │   ├── ldrToManifest.ts           # LDR → Manifest (for builder; download is direct)
│   │   └── voxelizer.ts
│   └── public/
│       ├── dorm_room_lego.ldr         # Downloadable LDraw file
│       ├── bedroom_lego_manifest.json
│       ├── Brick.png, banner.png, coin.svg, Comp 1.lottie
│       └── ...
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, CORS, routers
│   │   ├── api/
│   │   │   ├── endpoints.py           # /api/upload-video, /api/master-builder/process, Backboard
│   │   │   ├── lego_build_endpoint.py # LEGO voxel → manifest, instructions
│   │   │   ├── threejs_pipeline.py    # Three.js → voxels → LEGO → Backboard
│   │   │   └── solana_bb_coin.py      # verify-wallet, memo-payload, info
│   │   ├── models/                    # data_contracts, schemas
│   │   └── services/
│   │       ├── master_builder.py      # Greedy LEGO fitting
│   │       ├── threejs_voxelizer.py   # Three.js → voxel grid
│   │       ├── backboard_lego_memory.py
│   │       ├── backboard_service.py   # Optional Backboard integration
│   │       ├── twelve_labs.py         # Video upload, indexing, analyze
│   │       ├── rebrickable_api.py, piece_counter, part_discovery, ...
│   │       └── solana_bb_coin.py      # Memo build, verify, BB info
│   └── requirements.txt
├── TECHNOLOGY_SUMMARY.md     # Detailed tech: Backboard, algorithms, Gemini, Twelve Labs, Solana
├── README_LEGO_DETAILS.md   # LEGO model details, piece extraction, UI
└── README.md                # This file
```

---

## Prerequisites

- **Node.js** 18+ and **npm**
- **Python** 3.10+
- (Optional) **Backboard** SDK and API key for full AI/memory pipeline
- (Optional) **Twelve Labs** API key and index for video analysis
- (Optional) **Solana** RPC and wallet for BB Coins

---

## Getting Started

### 1. Frontend

```bash
cd frontend
npm install
npm run dev
```

- App: [http://localhost:3000](http://localhost:3000)

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # or: venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: [http://localhost:8000](http://localhost:8000)  
- Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Environment Variables

#### Frontend (`frontend/.env.local`)

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_GEMINI_API_KEY` | Gemini for instructions, video→3D, model analysis |
| `NEXT_PUBLIC_SOLANA_RPC_URL` | Solana RPC (defaults to devnet if unset) |
| `NEXT_PUBLIC_SOLANA_NETWORK` | e.g. `devnet` |
| `BB_COIN_MINT_ADDRESS` | (Optional) SPL mint for BB Coin |

#### Backend (`.env` or environment)

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Gemini (if used on backend) |
| `TWL_API_KEY` / `TWELVE_LABS_API_KEY` | Twelve Labs |
| `TWL_INDEX_ID` | Twelve Labs index |
| `BACKBOARD_API_KEY` | (Optional) Backboard |

---

## Main User Flows

1. **Upload room video** → Processing (with Lottie) → 3D dorm room in Environment panel.
2. **Process Video** → Backend/Twelve Labs path (or simulated) → LEGO manifest and instructions.
3. **View Details** (Full Set) → Opens instruction book; if no environment, shows “No Build Available” modal.
4. **Instruction book** → Flip pages, see piece counts and steps; **Download PDF** for LEGO-style manual.
5. **🧱 (Environment)** → Downloads `dorm_room_lego.ldr` to the user’s device.
6. **Add object (video)** → Object video → Gemini → Three.js object in scene + optional model/piece details.
7. **BB Coins (FAB)** → Connect wallet → View sample coins; “Save to BB Coin” sends Memo with LEGO metadata.

---

## API Overview

| Endpoint | Description |
|----------|-------------|
| `GET /` | Welcome message |
| `POST /api/upload-video` | Upload video file |
| `POST /api/master-builder/process` | Voxels → LEGO manifest (Master Builder) |
| `POST /api/lego/threejs-to-backboard` | Three.js → Voxels → LEGO → Backboard |
| `POST /api/lego/threejs-to-voxels` | Three.js scene → voxel list |
| `GET /api/lego/sample-dorm-voxels` | Sample dorm room voxels |
| `POST /api/solana/verify-wallet` | Verify wallet signature |
| `POST /api/solana/bb-coin/memo-payload` | Build Memo payload for LEGO metadata |
| `GET /api/solana/bb-coin/info` | Memo program and BB Coin info |
| `GET /api/backboard/{thread_id}/instructions` | Interactive instructions (Backboard) |
| `GET /api/backboard/{thread_id}/deltas` | Scene deltas (Backboard) |

---
