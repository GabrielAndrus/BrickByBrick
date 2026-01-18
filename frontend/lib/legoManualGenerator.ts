/**
 * LEGO Manual Generator
 * Processes brick manifests using greedy algorithm principles
 * and generates step-by-step building instructions with Backboard memory integration.
 */

// LEGO Part ID to Name mapping (common pieces)
export const PART_NAMES: Record<string, string> = {
  "3001": "Brick 2x4",
  "3002": "Brick 2x3",
  "3003": "Brick 2x2",
  "3004": "Brick 1x2",
  "3005": "Brick 1x1",
  "3009": "Brick 1x6",
  "3010": "Brick 1x4",
  "3622": "Brick 1x3",
  "3040": "Slope 45° 2x1",
  "3038": "Slope 45° Inverted 2x1",
  "3297": "Slope 33° 2x2",
  "3068": "Tile 2x2",
  "3069": "Tile 1x2",
  "3070": "Tile 1x1",
  "3024": "Plate 1x1",
  "3023": "Plate 1x2",
  "3022": "Plate 2x2",
  "3021": "Plate 2x3",
  "3020": "Plate 2x4",
  "3795": "Plate 2x6",
  "3034": "Plate 2x8",
  "3832": "Baseplate 32x32",
}

// LEGO Color ID to Name mapping
export const COLOR_NAMES: Record<number, string> = {
  0: "Black",
  1: "Blue",
  2: "Green",
  3: "Dark Turquoise",
  4: "Red",
  5: "Dark Pink",
  6: "Brown",
  7: "Light Gray",
  8: "Dark Gray",
  9: "Light Blue",
  10: "Bright Green",
  11: "Light Turquoise",
  12: "Salmon",
  13: "Pink",
  14: "Yellow",
  15: "White",
  16: "Light Green",
  17: "Light Yellow",
  19: "Tan",
  20: "Light Violet",
  22: "Purple",
  25: "Orange",
  26: "Magenta",
  27: "Lime",
  28: "Dark Tan",
  29: "Bright Pink",
  36: "Trans-Red",
  70: "Reddish Brown",
  71: "Light Bluish Gray",
  72: "Dark Bluish Gray",
  85: "Dark Purple",
}

// Piece price estimates (USD)
const PIECE_PRICES: Record<string, number> = {
  "3001": 0.10,
  "3002": 0.08,
  "3003": 0.06,
  "3004": 0.04,
  "3005": 0.03,
  "3009": 0.08,
  "3010": 0.06,
  "3068": 0.05,
  "3069": 0.03,
  "3070": 0.02,
  "3024": 0.02,
  "3023": 0.03,
  "3022": 0.04,
  "3811": 8.00, // Baseplate 32x32
  "10701": 15.00, // Baseplate 48x48
  "628": 5.00, // Baseplate 16x16
}

// Baseplate part IDs
const BASEPLATE_PARTS: Record<string, { size: number; name: string; price: number }> = {
  "628": { size: 16, name: "Baseplate 16×16", price: 5.00 },
  "3811": { size: 32, name: "Baseplate 32×32", price: 8.00 },
  "10701": { size: 48, name: "Baseplate 48×48", price: 15.00 },
}

export interface Brick {
  part_id: string
  position: number[]
  rotation: number
  color_id: number
  is_verified?: boolean
}

export interface ManifestData {
  manifest_version: string
  total_bricks: number
  bricks: Brick[]
}

export interface BuildStep {
  step_number: number
  layer_z: number
  bricks_in_step: Array<{
    part_id: string
    lego_type: string
    position: { studs: number[] }
    rotation: number
    color_id: number
    color_name: string
  }>
  piece_counts: Record<string, number>
  instructions: string
}

export interface PieceBreakdown {
  part_id: string
  color_id: number
  quantity: number
  piece_name: string
  color_name: string
  price_estimate: number
}

export interface PieceCount {
  total_pieces: number
  total_unique: number
  breakdown: PieceBreakdown[]
  by_category: Record<string, number>
  by_color: Record<string, number>
  estimated_cost: number
}

export interface InstructionManual {
  total_steps: number
  difficulty: string
  estimated_time_minutes: number
  baseplate?: {
    size_studs: number[]
    lego_type: string
    part_id?: string
  }
  steps: BuildStep[]
  layer_summary: Record<number, string>
}

export interface LegoMemoryEntry {
  build_id: string
  project_name: string
  room_type: string
  manifest: ManifestData
  piece_count: PieceCount
  instruction_manual: InstructionManual
  created_at: string
}

/**
 * Backboard Memory - Stores build history and component library
 */
class BackboardMemory {
  private builds: Map<string, LegoMemoryEntry> = new Map()
  private componentLibrary: Map<string, any> = new Map()

  saveBuild(entry: LegoMemoryEntry): void {
    this.builds.set(entry.build_id, entry)
    console.log(`[Backboard] Saved build: ${entry.build_id} - ${entry.project_name}`)
  }

  getBuild(buildId: string): LegoMemoryEntry | undefined {
    return this.builds.get(buildId)
  }

  getAllBuilds(): LegoMemoryEntry[] {
    return Array.from(this.builds.values())
  }

  saveComponent(componentId: string, data: any): void {
    this.componentLibrary.set(componentId, data)
  }

  getComponent(componentId: string): any {
    return this.componentLibrary.get(componentId)
  }
}

// Global Backboard instance
export const backboard = new BackboardMemory()

/**
 * Count pieces from manifest using greedy algorithm grouping
 * Always includes the required baseplate
 */
export function countPieces(manifest: ManifestData): PieceCount {
  const pieceCounts: Map<string, { count: number; colorId: number }> = new Map()
  const categoryMap: Record<string, number> = {}
  const colorMap: Record<string, number> = {}
  let totalCost = 0

  // First, calculate and add the baseplate
  let minX = Infinity, maxX = -Infinity
  let minY = Infinity, maxY = -Infinity
  
  for (const brick of manifest.bricks) {
    minX = Math.min(minX, brick.position[0])
    maxX = Math.max(maxX, brick.position[0])
    minY = Math.min(minY, brick.position[1])
    maxY = Math.max(maxY, brick.position[1])
  }
  
  const requiredSize = Math.max(Math.abs(maxX - minX) + 8, Math.abs(maxY - minY) + 8)
  let baseplateId = "3811" // Default 32x32
  let baseplateName = "Baseplate 32×32"
  let baseplatePrice = 8.00
  
  if (requiredSize <= 16) {
    baseplateId = "628"
    baseplateName = "Baseplate 16×16"
    baseplatePrice = 5.00
  } else if (requiredSize > 32) {
    baseplateId = "10701"
    baseplateName = "Baseplate 48×48"
    baseplatePrice = 15.00
  }

  // Add baseplate to counts
  pieceCounts.set(`${baseplateId}-28`, { count: 1, colorId: 28 }) // Dark Tan
  categoryMap["Baseplates"] = 1
  colorMap["Dark Tan"] = (colorMap["Dark Tan"] || 0) + 1
  totalCost += baseplatePrice

  // Count all bricks
  for (const brick of manifest.bricks) {
    const key = `${brick.part_id}-${brick.color_id}`
    const existing = pieceCounts.get(key) || { count: 0, colorId: brick.color_id }
    existing.count++
    pieceCounts.set(key, existing)

    // Category counting
    const partId = brick.part_id
    let category = "Bricks"
    if (partId.startsWith("306") || partId.startsWith("307")) category = "Tiles"
    else if (partId.startsWith("304") || partId.startsWith("303")) category = "Slopes"
    else if (partId.startsWith("302") || partId.startsWith("303") || partId.startsWith("379")) category = "Plates"
    categoryMap[category] = (categoryMap[category] || 0) + 1

    // Color counting
    const colorName = COLOR_NAMES[brick.color_id] || `Color ${brick.color_id}`
    colorMap[colorName] = (colorMap[colorName] || 0) + 1
  }

  // Build breakdown - put baseplate FIRST
  const breakdown: PieceBreakdown[] = []
  
  // Add baseplate as first item
  breakdown.push({
    part_id: baseplateId,
    color_id: 28,
    quantity: 1,
    piece_name: baseplateName,
    color_name: "Dark Tan",
    price_estimate: baseplatePrice
  })
  
  // Add all other pieces
  for (const [key, value] of pieceCounts.entries()) {
    const [partId, colorIdStr] = key.split('-')
    // Skip baseplate since we already added it
    if (partId === baseplateId) continue
    
    const colorId = parseInt(colorIdStr)
    const pieceName = PART_NAMES[partId] || `Part ${partId}`
    const colorName = COLOR_NAMES[colorId] || `Color ${colorId}`
    const pricePerPiece = PIECE_PRICES[partId] || 0.05
    const totalPrice = pricePerPiece * value.count
    totalCost += totalPrice

    breakdown.push({
      part_id: partId,
      color_id: colorId,
      quantity: value.count,
      piece_name: pieceName,
      color_name: colorName,
      price_estimate: totalPrice
    })
  }

  // Sort remaining pieces by quantity descending (keep baseplate first)
  const [baseplateEntry, ...restBreakdown] = breakdown
  restBreakdown.sort((a, b) => b.quantity - a.quantity)
  
  return {
    total_pieces: manifest.total_bricks + 1, // +1 for baseplate
    total_unique: pieceCounts.size,
    breakdown: [baseplateEntry, ...restBreakdown],
    by_category: categoryMap,
    by_color: colorMap,
    estimated_cost: Math.round(totalCost * 100) / 100
  }
}

/**
 * Calculate required baseplate size based on brick positions
 */
function calculateBaseplate(manifest: ManifestData): {
  part_id: string;
  size: number;
  name: string;
  size_studs: [number, number];
  price: number;
} {
  let minX = Infinity, maxX = -Infinity
  let minY = Infinity, maxY = -Infinity
  
  for (const brick of manifest.bricks) {
    minX = Math.min(minX, brick.position[0])
    maxX = Math.max(maxX, brick.position[0])
    minY = Math.min(minY, brick.position[1])
    maxY = Math.max(maxY, brick.position[1])
  }
  
  // Add padding for the baseplate
  const requiredWidth = Math.abs(maxX - minX) + 8
  const requiredDepth = Math.abs(maxY - minY) + 8
  const maxDimension = Math.max(requiredWidth, requiredDepth)
  
  // Select appropriate baseplate (greedy: use smallest that fits)
  if (maxDimension <= 16) {
    return { part_id: "628", size: 16, name: "Baseplate 16×16", size_studs: [16, 16], price: 5.00 }
  } else if (maxDimension <= 32) {
    return { part_id: "3811", size: 32, name: "Baseplate 32×32", size_studs: [32, 32], price: 8.00 }
  } else {
    return { part_id: "10701", size: 48, name: "Baseplate 48×48", size_studs: [48, 48], price: 15.00 }
  }
}

/**
 * Generate instruction manual using layer-by-layer greedy approach
 * Always includes a baseplate as Step 1
 */
export function generateInstructionManual(
  manifest: ManifestData,
  projectName: string = "LEGO Build"
): InstructionManual {
  // Calculate the required baseplate first (greedy selection)
  const baseplate = calculateBaseplate(manifest)
  
  // Group bricks by layer (z-coordinate)
  const bricksByLayer: Map<number, Brick[]> = new Map()
  
  for (const brick of manifest.bricks) {
    const z = brick.position[2]
    const layer = bricksByLayer.get(z) || []
    layer.push(brick)
    bricksByLayer.set(z, layer)
  }

  // Sort layers
  const sortedLayers = Array.from(bricksByLayer.keys()).sort((a, b) => a - b)

  // Generate steps - Step 1 is ALWAYS the baseplate
  const steps: BuildStep[] = []
  const layerSummary: Record<number, string> = {}
  
  // STEP 1: Place the baseplate foundation
  steps.push({
    step_number: 1,
    layer_z: -1, // Below all other layers
    bricks_in_step: [{
      part_id: baseplate.part_id,
      lego_type: baseplate.name,
      position: { studs: [0, 0, -1] },
      rotation: 0,
      color_id: 28, // Dark Tan (typical baseplate color)
      color_name: "Dark Tan"
    }],
    piece_counts: { [baseplate.part_id]: 1 },
    instructions: `Start with your ${baseplate.name}. Place it on a flat, stable surface. This will be the foundation for your entire build. The baseplate has ${baseplate.size}×${baseplate.size} studs to attach your bricks.`
  })
  layerSummary[-1] = "Foundation: Place your baseplate on a flat surface"
  
  let stepNumber = 2 // Start from 2 since baseplate is step 1

  for (const z of sortedLayers) {
    const bricksInLayer = bricksByLayer.get(z) || []
    
    // Count pieces for this layer
    const pieceCounts: Record<string, number> = {}
    const bricksForStep: BuildStep['bricks_in_step'] = []

    for (const brick of bricksInLayer) {
      pieceCounts[brick.part_id] = (pieceCounts[brick.part_id] || 0) + 1
      
      bricksForStep.push({
        part_id: brick.part_id,
        lego_type: PART_NAMES[brick.part_id] || `Part ${brick.part_id}`,
        position: { studs: brick.position },
        rotation: brick.rotation,
        color_id: brick.color_id,
        color_name: COLOR_NAMES[brick.color_id] || `Color ${brick.color_id}`
      })
    }

    // Sort bricks by position for logical ordering
    bricksForStep.sort((a, b) => {
      if (a.position.studs[0] !== b.position.studs[0]) {
        return a.position.studs[0] - b.position.studs[0]
      }
      return a.position.studs[1] - b.position.studs[1]
    })

    // Generate descriptive instruction text based on layer
    let instructions = ""
    const partsList = Object.entries(pieceCounts)
      .map(([id, qty]) => `${qty}× ${PART_NAMES[id] || `Part ${id}`}`)
      .join(', ')
    
    if (z === sortedLayers[0]) {
      instructions = `Build the first layer on your baseplate. Gather these pieces: ${partsList}. Place each brick carefully, making sure they click firmly onto the studs.`
    } else if (z === sortedLayers[sortedLayers.length - 1]) {
      instructions = `Final layer! You're almost done. Add these pieces to complete your build: ${partsList}. Make sure all bricks are securely attached.`
    } else {
      const layerNum = sortedLayers.indexOf(z) + 1
      instructions = `Continue building layer ${layerNum}. You'll need: ${partsList}. Stack these bricks on top of the previous layer.`
    }

    steps.push({
      step_number: stepNumber,
      layer_z: z,
      bricks_in_step: bricksForStep,
      piece_counts: pieceCounts,
      instructions
    })

    // Layer summary with helpful description
    if (z === sortedLayers[0]) {
      layerSummary[z] = "First layer: Building the foundation structure"
    } else if (z === sortedLayers[sortedLayers.length - 1]) {
      layerSummary[z] = "Top layer: Finishing touches"
    } else {
      layerSummary[z] = `Layer ${sortedLayers.indexOf(z) + 1}: Continue stacking bricks`
    }
    stepNumber++
  }

  // Estimate difficulty
  let difficulty = "Easy"
  if (manifest.total_bricks >= 100) difficulty = "Medium"
  if (manifest.total_bricks >= 200) difficulty = "Hard"
  if (manifest.total_bricks >= 400) difficulty = "Expert"

  // Estimate time (3 seconds per brick + 1 minute for baseplate setup)
  const estimatedTime = Math.max(5, Math.round((manifest.total_bricks * 3) / 60) + 1)

  return {
    total_steps: steps.length,
    difficulty,
    estimated_time_minutes: estimatedTime,
    baseplate: {
      size_studs: baseplate.size_studs,
      lego_type: baseplate.name,
      part_id: baseplate.part_id
    },
    steps,
    layer_summary: layerSummary
  }
}

/**
 * Process manifest and store in Backboard memory
 */
export function processManifestWithBackboard(
  manifest: ManifestData,
  projectName: string,
  roomType: string = "dorm_room"
): LegoMemoryEntry {
  const buildId = `build-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  
  console.log(`[LegoManualGenerator] Processing manifest with ${manifest.total_bricks} bricks`)
  
  // Count pieces using greedy grouping
  const pieceCount = countPieces(manifest)
  console.log(`[LegoManualGenerator] Counted ${pieceCount.total_pieces} pieces (${pieceCount.total_unique} unique)`)
  
  // Generate instruction manual
  const instructionManual = generateInstructionManual(manifest, projectName)
  console.log(`[LegoManualGenerator] Generated ${instructionManual.total_steps} instruction steps`)
  
  // Create memory entry
  const entry: LegoMemoryEntry = {
    build_id: buildId,
    project_name: projectName,
    room_type: roomType,
    manifest,
    piece_count: pieceCount,
    instruction_manual: instructionManual,
    created_at: new Date().toISOString()
  }
  
  // Save to Backboard
  backboard.saveBuild(entry)
  
  return entry
}

/**
 * Load manifest from JSON file
 */
export async function loadManifestFromFile(path: string): Promise<ManifestData> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`Failed to load manifest: ${response.statusText}`)
  }
  return response.json()
}
