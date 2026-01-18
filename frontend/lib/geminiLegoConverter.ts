/**
 * Gemini LEGO Converter
 * Uses Google Gemini AI to analyze 3D models and suggest optimal LEGO piece configurations
 * References the LEGO piece database for accurate part suggestions
 */

// Comprehensive LEGO Piece Database
export const LEGO_PIECE_DATABASE = {
  // === BRICKS (Standard height: 3 plates) ===
  bricks: {
    "3005": { name: "Brick 1×1", size: [1, 1, 1], category: "brick", common: true, description: "Small single stud brick" },
    "3004": { name: "Brick 1×2", size: [1, 2, 1], category: "brick", common: true, description: "Standard 2-stud brick" },
    "3622": { name: "Brick 1×3", size: [1, 3, 1], category: "brick", common: true, description: "Medium length brick" },
    "3010": { name: "Brick 1×4", size: [1, 4, 1], category: "brick", common: true, description: "Long single-row brick" },
    "3009": { name: "Brick 1×6", size: [1, 6, 1], category: "brick", common: true, description: "Extra long single-row brick" },
    "3008": { name: "Brick 1×8", size: [1, 8, 1], category: "brick", common: true, description: "Very long single-row brick" },
    "3003": { name: "Brick 2×2", size: [2, 2, 1], category: "brick", common: true, description: "Square brick, good for corners" },
    "3002": { name: "Brick 2×3", size: [2, 3, 1], category: "brick", common: true, description: "Medium rectangular brick" },
    "3001": { name: "Brick 2×4", size: [2, 4, 1], category: "brick", common: true, description: "Classic LEGO brick, most common" },
    "3007": { name: "Brick 2×8", size: [2, 8, 1], category: "brick", common: true, description: "Long rectangular brick" },
    "3006": { name: "Brick 2×10", size: [2, 10, 1], category: "brick", common: false, description: "Extra long rectangular brick" },
  },
  
  // === PLATES (1/3 height of bricks) ===
  plates: {
    "3024": { name: "Plate 1×1", size: [1, 1, 0.33], category: "plate", common: true, description: "Tiny single stud plate" },
    "3023": { name: "Plate 1×2", size: [1, 2, 0.33], category: "plate", common: true, description: "Small 2-stud plate" },
    "3623": { name: "Plate 1×3", size: [1, 3, 0.33], category: "plate", common: true, description: "Medium plate" },
    "3710": { name: "Plate 1×4", size: [1, 4, 0.33], category: "plate", common: true, description: "Long thin plate" },
    "3666": { name: "Plate 1×6", size: [1, 6, 0.33], category: "plate", common: true, description: "Extra long thin plate" },
    "3022": { name: "Plate 2×2", size: [2, 2, 0.33], category: "plate", common: true, description: "Square plate" },
    "3021": { name: "Plate 2×3", size: [2, 3, 0.33], category: "plate", common: true, description: "Medium rectangular plate" },
    "3020": { name: "Plate 2×4", size: [2, 4, 0.33], category: "plate", common: true, description: "Standard rectangular plate" },
    "3795": { name: "Plate 2×6", size: [2, 6, 0.33], category: "plate", common: true, description: "Long rectangular plate" },
    "3034": { name: "Plate 2×8", size: [2, 8, 0.33], category: "plate", common: true, description: "Very long rectangular plate" },
  },
  
  // === TILES (Smooth top, no studs) ===
  tiles: {
    "3070": { name: "Tile 1×1", size: [1, 1, 0.33], category: "tile", common: true, description: "Smooth single stud tile" },
    "3069": { name: "Tile 1×2", size: [1, 2, 0.33], category: "tile", common: true, description: "Smooth 2-stud tile" },
    "63864": { name: "Tile 1×3", size: [1, 3, 0.33], category: "tile", common: true, description: "Smooth medium tile" },
    "2431": { name: "Tile 1×4", size: [1, 4, 0.33], category: "tile", common: true, description: "Smooth long tile" },
    "3068": { name: "Tile 2×2", size: [2, 2, 0.33], category: "tile", common: true, description: "Smooth square tile" },
    "87079": { name: "Tile 2×4", size: [2, 4, 0.33], category: "tile", common: true, description: "Smooth rectangular tile" },
  },
  
  // === SLOPES (Angled pieces) ===
  slopes: {
    "54200": { name: "Slope 1×1×2/3", size: [1, 1, 0.67], category: "slope", angle: 30, description: "Small cheese slope" },
    "85984": { name: "Slope 1×2×2/3", size: [1, 2, 0.67], category: "slope", angle: 30, description: "Cheese slope, 2 studs" },
    "3040": { name: "Slope 45° 2×1", size: [2, 1, 1], category: "slope", angle: 45, description: "Standard 45-degree slope" },
    "3039": { name: "Slope 45° 2×2", size: [2, 2, 1], category: "slope", angle: 45, description: "Square 45-degree slope" },
    "3038": { name: "Slope 45° 2×3", size: [2, 3, 1], category: "slope", angle: 45, description: "Long 45-degree slope" },
    "3037": { name: "Slope 45° 2×4", size: [2, 4, 1], category: "slope", angle: 45, description: "Extra long 45-degree slope" },
    "3298": { name: "Slope 33° 2×2", size: [2, 2, 1], category: "slope", angle: 33, description: "Gentler slope for roofs" },
    "3297": { name: "Slope 33° 3×2", size: [3, 2, 1], category: "slope", angle: 33, description: "Wide gentle slope" },
  },
  
  // === INVERTED SLOPES ===
  invertedSlopes: {
    "3665": { name: "Slope Inverted 45° 2×1", size: [2, 1, 1], category: "inverted_slope", angle: 45, description: "Upside-down slope" },
    "3660": { name: "Slope Inverted 45° 2×2", size: [2, 2, 1], category: "inverted_slope", angle: 45, description: "Square inverted slope" },
  },
  
  // === CURVED/ROUND PIECES ===
  curved: {
    "3062": { name: "Brick Round 1×1", size: [1, 1, 1], category: "round", description: "Cylindrical brick" },
    "3941": { name: "Brick Round 2×2", size: [2, 2, 1], category: "round", description: "Round 2×2 brick" },
    "6091": { name: "Brick Curved 1×2×1⅓", size: [1, 2, 1.33], category: "curved", description: "Curved top brick" },
    "11477": { name: "Slope Curved 2×1", size: [2, 1, 0.67], category: "curved", description: "Smooth curved slope" },
    "15068": { name: "Slope Curved 2×2", size: [2, 2, 0.67], category: "curved", description: "Wide curved slope" },
  },
  
  // === SPECIAL PIECES ===
  special: {
    "3794": { name: "Plate 1×2 with 1 Stud", size: [1, 2, 0.33], category: "special", description: "Jumper plate" },
    "87580": { name: "Plate 2×2 with 1 Stud", size: [2, 2, 0.33], category: "special", description: "2×2 jumper plate" },
    "4070": { name: "Brick Modified 1×1 with Headlight", size: [1, 1, 1], category: "special", description: "Headlight brick, side stud" },
    "2877": { name: "Brick Modified 1×2 with Grille", size: [1, 2, 1], category: "special", description: "Grille brick for vents" },
    "98283": { name: "Brick Modified 1×2 with Masonry", size: [1, 2, 1], category: "special", description: "Textured brick wall look" },
  },
  
  // === BASEPLATES ===
  baseplates: {
    "628": { name: "Baseplate 16×16", size: [16, 16, 0.33], category: "baseplate", description: "Small baseplate" },
    "3811": { name: "Baseplate 32×32", size: [32, 32, 0.33], category: "baseplate", description: "Standard baseplate" },
    "10701": { name: "Baseplate 48×48", size: [48, 48, 0.33], category: "baseplate", description: "Large baseplate" },
  },
};

// Flatten database for easy lookup
export const ALL_PIECES: Record<string, any> = {
  ...LEGO_PIECE_DATABASE.bricks,
  ...LEGO_PIECE_DATABASE.plates,
  ...LEGO_PIECE_DATABASE.tiles,
  ...LEGO_PIECE_DATABASE.slopes,
  ...LEGO_PIECE_DATABASE.invertedSlopes,
  ...LEGO_PIECE_DATABASE.curved,
  ...LEGO_PIECE_DATABASE.special,
  ...LEGO_PIECE_DATABASE.baseplates,
};

// LEGO Colors with RGB values
export const LEGO_COLORS = {
  0: { name: "Black", rgb: "#1B1B1B" },
  1: { name: "Blue", rgb: "#0055BF" },
  2: { name: "Green", rgb: "#237841" },
  4: { name: "Red", rgb: "#C91A09" },
  5: { name: "Dark Pink", rgb: "#C870A0" },
  6: { name: "Brown", rgb: "#583927" },
  7: { name: "Light Gray", rgb: "#9BA19D" },
  8: { name: "Dark Gray", rgb: "#6D6E5C" },
  14: { name: "Yellow", rgb: "#F2CD37" },
  15: { name: "White", rgb: "#FFFFFF" },
  19: { name: "Tan", rgb: "#E4CD9E" },
  25: { name: "Orange", rgb: "#FE8A18" },
  28: { name: "Dark Tan", rgb: "#958A73" },
  70: { name: "Reddish Brown", rgb: "#582A12" },
  71: { name: "Light Bluish Gray", rgb: "#A0A5A9" },
  72: { name: "Dark Bluish Gray", rgb: "#6C6E68" },
};

export interface ModelInterpretation {
  id: string;
  name: string;
  description: string;
  style: 'realistic' | 'simplified' | 'stylized' | 'micro';
  pieceCount: number;
  difficulty: string;
  suggestedPieces: Array<{
    part_id: string;
    name: string;
    quantity: number;
    reason: string;
    alternatives?: string[];
  }>;
  buildNotes: string[];
}

export interface ConversionResult {
  interpretations: ModelInterpretation[];
  abstractShapeSuggestions: Array<{
    shape: string;
    suggestedPieces: string[];
    technique: string;
  }>;
  colorMappings: Array<{
    originalColor: string;
    legoColorId: number;
    legoColorName: string;
  }>;
}

/**
 * Generate Gemini prompt with LEGO piece knowledge
 */
function buildLegoConversionPrompt(
  pieceList: Array<{ part_id: string; quantity: number; piece_name: string }>,
  roomType: string,
  totalBricks: number
): string {
  // Build piece database reference
  const pieceReference = Object.entries(ALL_PIECES)
    .slice(0, 30)
    .map(([id, info]) => `- ${id}: ${info.name} (${info.size.join('×')}) - ${info.description}`)
    .join('\n');

  const currentPieces = pieceList
    .slice(0, 15)
    .map(p => `- ${p.quantity}× ${p.piece_name} (${p.part_id})`)
    .join('\n');

  return `You are a LEGO Master Builder AI. Analyze the following LEGO build and suggest multiple model interpretations.

## Current Build Information
- Room Type: ${roomType}
- Total Bricks: ${totalBricks}
- Current Pieces Used:
${currentPieces}

## LEGO Piece Database Reference
${pieceReference}

## Your Task
Create 3 different interpretations of how to build this model:

1. **Realistic** - Detailed build with more pieces for accurate representation
2. **Simplified** - Fewer pieces, easier to build, good for beginners
3. **Stylized** - Creative interpretation using special pieces

For each interpretation, provide:
1. Name and description
2. Difficulty level (Easy/Medium/Hard/Expert)
3. Estimated piece count
4. Key piece suggestions with reasoning
5. Techniques for abstract shapes (curves, angles, textures)
6. Build notes and tips

## Response Format (JSON)
{
  "interpretations": [
    {
      "id": "realistic",
      "name": "Detailed Build Name",
      "description": "Description of this interpretation",
      "style": "realistic",
      "pieceCount": 200,
      "difficulty": "Hard",
      "suggestedPieces": [
        {
          "part_id": "3001",
          "name": "Brick 2×4",
          "quantity": 20,
          "reason": "Primary structural brick",
          "alternatives": ["3002", "3003"]
        }
      ],
      "buildNotes": ["Start with the base", "Use plates for details"]
    }
  ],
  "abstractShapeSuggestions": [
    {
      "shape": "curved wall",
      "suggestedPieces": ["11477", "15068"],
      "technique": "Stack curved slopes in alternating directions"
    }
  ],
  "colorMappings": [
    {
      "originalColor": "#FFFFFF",
      "legoColorId": 15,
      "legoColorName": "White"
    }
  ]
}

Be creative but practical. Reference real LEGO building techniques.`;
}

/**
 * Use Gemini to generate model interpretations
 */
export async function generateModelInterpretations(
  pieceList: Array<{ part_id: string; quantity: number; piece_name: string }>,
  roomType: string,
  totalBricks: number,
  apiKey: string
): Promise<ConversionResult> {
  if (!apiKey || apiKey.trim() === '') {
    console.error('[GeminiLegoConverter] Error: API key is missing. Please set GEMINI_API_KEY in .env');
    return getDefaultInterpretations(pieceList, totalBricks);
  }

  const { GoogleGenerativeAI } = await import('@google/generative-ai');
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({ model: 'gemini-pro' });

  const prompt = buildLegoConversionPrompt(pieceList, roomType, totalBricks);

  try {
    const result = await model.generateContent(prompt);
    const text = result.response.text();
    
    // Extract JSON from response
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      return {
        interpretations: parsed.interpretations || [],
        abstractShapeSuggestions: parsed.abstractShapeSuggestions || [],
        colorMappings: parsed.colorMappings || [],
      };
    }
  } catch (error) {
    console.error('[GeminiLegoConverter] Error:', error);
  }

  // Return default interpretations if Gemini fails
  return getDefaultInterpretations(pieceList, totalBricks);
}

/**
 * Get default interpretations without AI
 */
function getDefaultInterpretations(
  pieceList: Array<{ part_id: string; quantity: number; piece_name: string }>,
  totalBricks: number
): ConversionResult {
  return {
    interpretations: [
      {
        id: 'realistic',
        name: 'Detailed Recreation',
        description: 'A detailed brick-by-brick recreation with attention to structural accuracy',
        style: 'realistic',
        pieceCount: totalBricks,
        difficulty: totalBricks > 200 ? 'Hard' : totalBricks > 100 ? 'Medium' : 'Easy',
        suggestedPieces: pieceList.slice(0, 10).map(p => ({
          part_id: p.part_id,
          name: p.piece_name,
          quantity: p.quantity,
          reason: 'Core structural piece',
        })),
        buildNotes: [
          'Start with the baseplate foundation',
          'Build layer by layer from bottom to top',
          'Ensure bricks interlock properly for stability',
        ],
      },
      {
        id: 'simplified',
        name: 'Simple Build',
        description: 'A simplified version using fewer pieces while maintaining recognizable form',
        style: 'simplified',
        pieceCount: Math.floor(totalBricks * 0.6),
        difficulty: 'Easy',
        suggestedPieces: pieceList.slice(0, 5).map(p => ({
          part_id: p.part_id,
          name: p.piece_name,
          quantity: Math.floor(p.quantity * 0.6),
          reason: 'Essential piece for basic structure',
        })),
        buildNotes: [
          'Focus on main shapes, skip small details',
          'Use larger pieces where possible',
          'Great for younger builders',
        ],
      },
      {
        id: 'stylized',
        name: 'Creative Interpretation',
        description: 'An artistic take using special pieces for unique textures and effects',
        style: 'stylized',
        pieceCount: Math.floor(totalBricks * 0.8),
        difficulty: 'Medium',
        suggestedPieces: [
          { part_id: '98283', name: 'Masonry Brick', quantity: 20, reason: 'Adds wall texture' },
          { part_id: '11477', name: 'Curved Slope', quantity: 15, reason: 'Smooth architectural curves' },
          ...pieceList.slice(0, 3).map(p => ({
            part_id: p.part_id,
            name: p.piece_name,
            quantity: p.quantity,
            reason: 'Base structure',
          })),
        ],
        buildNotes: [
          'Mix standard bricks with textured pieces',
          'Use slopes for modern architectural look',
          'Consider color contrast for visual interest',
        ],
      },
    ],
    abstractShapeSuggestions: [
      {
        shape: 'Curved surfaces',
        suggestedPieces: ['11477', '15068', '6091'],
        technique: 'Layer curved slopes or use round bricks',
      },
      {
        shape: 'Angled walls',
        suggestedPieces: ['3040', '3039', '3037'],
        technique: 'Use 45° slopes with standard bricks',
      },
      {
        shape: 'Textured walls',
        suggestedPieces: ['98283', '2877'],
        technique: 'Alternate masonry and grille bricks',
      },
    ],
    colorMappings: [],
  };
}

/**
 * Suggest pieces for abstract shapes
 */
export function suggestPiecesForShape(shapeDescription: string): {
  pieces: Array<{ id: string; name: string; reason: string }>;
  technique: string;
} {
  const shapeLower = shapeDescription.toLowerCase();
  
  if (shapeLower.includes('curve') || shapeLower.includes('round')) {
    return {
      pieces: [
        { id: '11477', name: 'Slope Curved 2×1', reason: 'Creates smooth curves' },
        { id: '15068', name: 'Slope Curved 2×2', reason: 'Wider curved surface' },
        { id: '3062', name: 'Brick Round 1×1', reason: 'Cylindrical elements' },
      ],
      technique: 'Stack curved slopes at alternating angles, or use round bricks for pillars',
    };
  }
  
  if (shapeLower.includes('angle') || shapeLower.includes('slope') || shapeLower.includes('roof')) {
    return {
      pieces: [
        { id: '3040', name: 'Slope 45° 2×1', reason: 'Standard roof angle' },
        { id: '3298', name: 'Slope 33° 2×2', reason: 'Gentler slope for modern roofs' },
        { id: '3665', name: 'Inverted Slope', reason: 'Underside angles' },
      ],
      technique: 'Combine regular and inverted slopes for complex angles',
    };
  }
  
  if (shapeLower.includes('texture') || shapeLower.includes('detail')) {
    return {
      pieces: [
        { id: '98283', name: 'Masonry Brick', reason: 'Stone/brick wall texture' },
        { id: '2877', name: 'Grille Brick', reason: 'Vent/grate texture' },
        { id: '3070', name: 'Tile 1×1', reason: 'Smooth surface details' },
      ],
      technique: 'Mix textured bricks with standard bricks for visual interest',
    };
  }
  
  // Default suggestion
  return {
    pieces: [
      { id: '3001', name: 'Brick 2×4', reason: 'Versatile standard brick' },
      { id: '3020', name: 'Plate 2×4', reason: 'Thin horizontal layers' },
      { id: '3068', name: 'Tile 2×2', reason: 'Smooth finishing' },
    ],
    technique: 'Use combination of bricks, plates, and tiles for varied heights and textures',
  };
}

/**
 * Simple LEGO conversion - takes piece count and returns LEGO build suggestions
 * Now with support for specific model analysis from Three.js generated objects
 */
export async function convertToLegoDesign(
  totalPieces: number,
  pieceBreakdown: Array<{ part_id: string; quantity: number; piece_name: string; color_id?: number; color_name?: string }>,
  modelDescription: string,
  apiKey: string,
  modelAnalysis?: {
    modelName: string;
    modelType: string;
    description: string;
    extractedPieces: Array<{
      part_id: string;
      name: string;
      quantity: number;
      color_id?: number;
      color_name?: string;
      reasoning: string;
    }>;
  }
): Promise<string> {
  if (!apiKey || apiKey.trim() === '') {
    console.error('[GeminiLegoConverter] Error: API key is missing. Please set GEMINI_API_KEY in .env');
    return 'Unable to generate LEGO design without API key';
  }

  const { GoogleGenerativeAI } = await import('@google/generative-ai');
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({ model: 'gemini-pro' });

  // Use model analysis pieces if available, otherwise use environment pieces
  const piecesToUse = modelAnalysis?.extractedPieces || pieceBreakdown;
  
  const currentPieces = piecesToUse
    .slice(0, 20)
    .map(p => {
      const colorInfo = (p as any).color_name ? ` (${(p as any).color_name})` : '';
      const reasoning = (p as any).reasoning ? ` - ${(p as any).reasoning}` : '';
      return `- ${p.quantity}× ${p.name}${colorInfo}${reasoning}`;
    })
    .join('\n');

  // Build specific prompt based on whether we have model analysis
  let prompt = '';
  if (modelAnalysis) {
    prompt = `You are a LEGO Master Builder expert. You are building a detailed instruction manual for a specific LEGO model.

## Specific Model Details
- **Model Name**: ${modelAnalysis.modelName}
- **Model Type**: ${modelAnalysis.modelType}
- **Description**: ${modelAnalysis.description}

## Pieces Specifically Extracted from the 3D Design
${currentPieces}

## Your Task
Create detailed, step-by-step LEGO building instructions that:
1. Use EXACTLY the pieces and colors identified from the 3D model
2. Show how to build this ${modelAnalysis.modelName} authentically
3. Explain placement and orientation of each piece type
4. Describe color placement for visual accuracy
5. Include construction techniques specific to this design

Focus on the specific pieces that make this model unique. Be detailed about assembly sequences.`;
  } else {
    prompt = `You are a LEGO Master Builder. Convert the following 3D model into a LEGO brick design.

## Model Information
- Description: ${modelDescription}
- Total Pieces Needed: ${totalPieces}
- Current Pieces Breakdown (by piece type and color):
${currentPieces}

## Task
Provide a creative LEGO interpretation of this model that:
1. Uses realistic LEGO building techniques
2. Incorporates the actual pieces and colors listed above
3. Suggests how to position each piece type for authentic appearance
4. Describes key structural and color composition techniques

Be specific about which color pieces go where for the best visual result.
Keep the response concise and practical. Focus on how to build this in LEGO form using these exact pieces and colors.`;
  }

  try {
    const result = await model.generateContent(prompt);
    const text = result.response.text();
    console.log('[GeminiLegoConverter] Successfully generated LEGO design');
    return text;
  } catch (error: any) {
    console.error('[GeminiLegoConverter] Full error:', error);
    const errorMessage = error?.message || String(error);
    
    // Check for quota/rate limit errors
    if (errorMessage.includes('429') || errorMessage.includes('quota') || errorMessage.includes('Quota')) {
      return `API quota exceeded. Please wait a few minutes before trying again. Rate limits apply to the free tier of the Gemini API.`;
    }
    
    // Check for other API errors
    if (errorMessage.includes('403') || errorMessage.includes('permission')) {
      return `API authentication error. Please verify your API key is valid.`;
    }
    
    return `Failed to generate LEGO design: ${errorMessage}`;
  }
}

/**
 * Get piece info from database
 */
export function getPieceInfo(partId: string): typeof ALL_PIECES[string] | null {
  return ALL_PIECES[partId] || null;
}

/**
 * Find similar pieces
 */
export function findSimilarPieces(partId: string): string[] {
  const piece = ALL_PIECES[partId];
  if (!piece) return [];
  
  const [w, d, h] = piece.size;
  const category = piece.category;
  
  return Object.entries(ALL_PIECES)
    .filter(([id, info]) => {
      if (id === partId) return false;
      if (info.category !== category) return false;
      const [pw, pd, ph] = info.size;
      // Similar size (within 2 studs)
      return Math.abs(pw * pd - w * d) <= 4;
    })
    .map(([id]) => id)
    .slice(0, 5);
}
