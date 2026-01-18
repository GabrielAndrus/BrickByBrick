/**
 * Extract LEGO piece information from Three.js generated code
 * Maps 3D geometries to actual LEGO pieces and identifies the model
 */

export interface ThreeJSModelAnalysis {
  modelName: string;
  modelType: string; // e.g., "House", "Car", "Animal", "Furniture"
  estimatedSetNumber?: string;
  description: string;
  legoSetComparison?: {
    officialSetNumber?: string;
    officialName?: string;
    yearReleased?: number;
  };
  extractedPieces: Array<{
    part_id: string;
    name: string;
    quantity: number;
    color_id?: number;
    color_name?: string;
    reasoning: string;
  }>;
  structuralAnalysis: {
    baseSize: { width: number; depth: number };
    height: number;
    estimatedTotalPieces: number;
    buildComplexity: 'Simple' | 'Intermediate' | 'Advanced' | 'Expert';
  };
  keyFeatures: string[];
}

/**
 * Analyze Three.js code to identify LEGO pieces and model type
 */
export async function analyzeThreeJSForLegoPieces(
  threeJSCode: string,
  objectName: string,
  apiKey: string
): Promise<ThreeJSModelAnalysis> {
  const { GoogleGenerativeAI } = await import('@google/generative-ai');
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({ model: 'gemini-pro' });

  // Truncate code if too long
  const codeSample = threeJSCode.substring(0, 2000);

  const prompt = `You are a LEGO Master Builder expert and Three.js developer. 

Analyze this Three.js code for a "${objectName}" and identify:
1. What specific LEGO model this resembles (real LEGO set if possible)
2. The major geometric shapes and their sizes
3. Which LEGO pieces would be used to recreate this
4. Color scheme and color-to-piece mapping
5. Build complexity level

Three.js Code:
\`\`\`javascript
${codeSample}
\`\`\`

Return a JSON response with this exact structure:
{
  "modelName": "Specific model name (e.g., 'Classic Farmhouse', 'Sports Car')",
  "modelType": "Category (e.g., House, Car, Animal, Furniture, Landmark)",
  "estimatedSetNumber": "If this resembles a real LEGO set, the set number (e.g., 10190)",
  "description": "Detailed description of the model",
  "legoSetComparison": {
    "officialSetNumber": "Real LEGO set number if applicable",
    "officialName": "Official LEGO set name if applicable",
    "yearReleased": 2024
  },
  "extractedPieces": [
    {
      "part_id": "3001",
      "name": "Brick 2×4",
      "quantity": 25,
      "color_id": 0,
      "color_name": "Black",
      "reasoning": "Main structural walls"
    },
    {
      "part_id": "3023",
      "name": "Plate 1×2",
      "quantity": 12,
      "color_id": 15,
      "color_name": "White",
      "reasoning": "Roof details"
    }
  ],
  "structuralAnalysis": {
    "baseSize": { "width": 32, "depth": 24 },
    "height": 28,
    "estimatedTotalPieces": 250,
    "buildComplexity": "Intermediate"
  },
  "keyFeatures": [
    "Realistic proportions",
    "Color contrast details",
    "Stable base structure"
  ]
}

Be specific and practical. Reference real LEGO pieces by their official part IDs.`;

  try {
    const result = await model.generateContent(prompt);
    const text = result.response.text();

    // Extract JSON from response
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]);
    }

    // If no JSON found, create a default analysis
    return createDefaultAnalysis(objectName);
  } catch (error) {
    console.error('[ThreeJSToLego] Analysis error:', error);
    return createDefaultAnalysis(objectName);
  }
}

/**
 * Create a default analysis when AI fails
 */
function createDefaultAnalysis(objectName: string): ThreeJSModelAnalysis {
  return {
    modelName: objectName,
    modelType: 'Generic Object',
    description: `A Three.js generated ${objectName}. Analyze the geometry to determine optimal LEGO piece configuration.`,
    extractedPieces: [
      {
        part_id: '3001',
        name: 'Brick 2×4',
        quantity: 20,
        color_id: 0,
        color_name: 'Black',
        reasoning: 'Primary structural component',
      },
      {
        part_id: '3002',
        name: 'Brick 2×3',
        quantity: 15,
        color_id: 1,
        color_name: 'Blue',
        reasoning: 'Accent structural element',
      },
      {
        part_id: '3020',
        name: 'Plate 2×4',
        quantity: 8,
        color_id: 15,
        color_name: 'White',
        reasoning: 'Base and detail plates',
      },
    ],
    structuralAnalysis: {
      baseSize: { width: 16, depth: 16 },
      height: 12,
      estimatedTotalPieces: 100,
      buildComplexity: 'Intermediate',
    },
    keyFeatures: [
      'Modular construction',
      'Color-coded sections',
      'Stable base foundation',
    ],
  };
}

/**
 * Parse geometric dimensions from Three.js code
 */
export function parseThreeJSGeometries(code: string): Array<{
  type: string;
  dimensions: { w?: number; h?: number; d?: number };
  count: number;
}> {
  const geometries: Array<{ type: string; dimensions: any; count: number }> = [];

  // Find BoxGeometry instances
  const boxRegex = /new\s+THREE\.BoxGeometry\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\)/g;
  let boxMatch;
  const boxGeometries: Record<string, number> = {};

  while ((boxMatch = boxRegex.exec(code)) !== null) {
    const dims = `${boxMatch[1]},${boxMatch[2]},${boxMatch[3]}`;
    boxGeometries[dims] = (boxGeometries[dims] || 0) + 1;
  }

  Object.entries(boxGeometries).forEach(([dims, count]) => {
    geometries.push({
      type: 'Box',
      dimensions: { w: 1, h: 1, d: 1 }, // Placeholder - would need actual parsing
      count,
    });
  });

  // Find SphereGeometry instances
  const sphereRegex = /new\s+THREE\.SphereGeometry\s*\(\s*([^,]+),/g;
  const sphereCount = (code.match(sphereRegex) || []).length;
  if (sphereCount > 0) {
    geometries.push({
      type: 'Sphere',
      dimensions: { w: 1 },
      count: sphereCount,
    });
  }

  // Find CylinderGeometry instances
  const cylinderRegex = /new\s+THREE\.CylinderGeometry/g;
  const cylinderCount = (code.match(cylinderRegex) || []).length;
  if (cylinderCount > 0) {
    geometries.push({
      type: 'Cylinder',
      dimensions: { w: 1, h: 1 },
      count: cylinderCount,
    });
  }

  return geometries;
}

/**
 * Map Three.js geometries to LEGO pieces
 */
export function mapGeometriesToLegoPieces(geometries: ReturnType<typeof parseThreeJSGeometries>) {
  const pieceMappings: Array<{ geometry: string; suggestedParts: string[] }> = [
    {
      geometry: 'Box',
      suggestedParts: ['3001', '3002', '3003', '3004', '3010'], // Various brick sizes
    },
    {
      geometry: 'Sphere',
      suggestedParts: ['3941', '3062'], // Round bricks
    },
    {
      geometry: 'Cylinder',
      suggestedParts: ['3941', '11477'], // Round and curved pieces
    },
  ];

  return geometries.map(geom => {
    const mapping = pieceMappings.find(m => m.geometry === geom.type);
    return {
      ...geom,
      suggestedLegoParts: mapping?.suggestedParts || ['3001'], // Default to 2×4 brick
    };
  });
}
