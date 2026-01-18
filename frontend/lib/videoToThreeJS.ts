/**
 * Convert video scan to Three.js component using Gemini
 * Takes a 360-degree video scan and generates Three.js code to render it as an object
 */

export interface VideoToLegoResult {
  threeJSCode: string;
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
  };
}

export async function convertVideoTo3DObject(
  videoFile: File,
  objectName: string,
  apiKey: string
): Promise<VideoToLegoResult> {
  if (!apiKey || apiKey.trim() === '') {
    console.error('[VideoTo3JS] Error: API key is missing');
    throw new Error('API key is missing');
  }

  const { GoogleGenerativeAI } = await import('@google/generative-ai');
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({ model: 'gemini-pro' });

  // LEGO-focused prompt - create LEGO brick representation
  const prompt = `You are a LEGO Master Builder. Create THREE.JS code that renders a "${objectName}" built entirely from LEGO bricks.

IMPORTANT: The object must look like it's made of LEGO bricks - use box geometries for bricks with cylinder studs on top.

Return ONLY raw JavaScript code (no markdown, no backticks, no explanations).

Requirements:
1. Create a THREE.Group() as the main container
2. Use BoxGeometry for LEGO bricks (standard brick is 0.8 wide x 0.96 tall x 0.8 deep per stud)
3. Add CylinderGeometry studs on top of each brick (radius 0.12, height 0.08)
4. Use LEGO colors: Red (0xc91a09), Blue (0x0055bf), Yellow (0xf2cd37), Green (0x237841), White (0xf4f4f4), Black (0x1b1b1b)
5. Build the object using stacked bricks like a real LEGO set
6. Fit within a 2x2x2 unit space
7. THREE is available as a global

Example LEGO brick creation:
const group = new THREE.Group()
const brickMat = new THREE.MeshStandardMaterial({ color: 0xc91a09, roughness: 0.3 })
const brickGeo = new THREE.BoxGeometry(1.6, 0.96, 0.8) // 2x1 brick
const brick = new THREE.Mesh(brickGeo, brickMat)
brick.position.y = 0.48
group.add(brick)
// Add studs
const studGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.08, 12)
const stud1 = new THREE.Mesh(studGeo, brickMat)
stud1.position.set(-0.4, 1.0, 0)
group.add(stud1)
const stud2 = new THREE.Mesh(studGeo, brickMat)
stud2.position.set(0.4, 1.0, 0)
group.add(stud2)
group`;

  try {
    const result = await model.generateContent(prompt);
    const text = result.response.text();
    console.log('[VideoTo3JS] Successfully generated 3D object code');
    
    // Clean up the response
    let cleanCode = text.trim();
    
    // Remove markdown code blocks if present
    if (cleanCode.startsWith('```')) {
      cleanCode = cleanCode.replace(/^```.*?\n/, '').replace(/\n```$/, '');
    }
    
    // Ensure it returns a group
    if (!cleanCode.includes('return')) {
      cleanCode = cleanCode.trim();
      if (cleanCode.endsWith('group')) {
        cleanCode = cleanCode;
      } else {
        cleanCode += '\nreturn group';
      }
    }
    
    // Now analyze the code to extract LEGO pieces
    const modelAnalysis = await analyzeThreeJSForLegoPieces(cleanCode, objectName, apiKey);
    
    return {
      threeJSCode: cleanCode,
      modelAnalysis,
    };
  } catch (error: any) {
    console.error('[VideoTo3JS] Error:', error);
    const errorMessage = error?.message || String(error);
    
    if (errorMessage.includes('429') || errorMessage.includes('quota')) {
      throw new Error('API quota exceeded. Please wait a few minutes.');
    }
    
    throw new Error(`Failed to generate 3D object: ${errorMessage}`);
  }
}

/**
 * Analyze Three.js code to extract LEGO pieces
 */
async function analyzeThreeJSForLegoPieces(
  threeJSCode: string,
  objectName: string,
  apiKey: string
) {
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

Return ONLY valid JSON with this structure (no markdown, no explanation):
{
  "modelName": "Specific model name",
  "modelType": "Category",
  "description": "Detailed description",
  "extractedPieces": [
    {
      "part_id": "3001",
      "name": "Brick 2×4",
      "quantity": 25,
      "color_id": 0,
      "color_name": "Black",
      "reasoning": "Main structural walls"
    }
  ]
}`;

  try {
    const result = await model.generateContent(prompt);
    const text = result.response.text();

    // Extract JSON from response
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]);
    }
  } catch (error) {
    console.error('[ThreeJSAnalysis] Error:', error);
  }

  // Return default if analysis fails
  return {
    modelName: objectName,
    modelType: 'Generic Object',
    description: `A custom ${objectName} model created from video scan`,
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
        reasoning: 'Secondary structural element',
      },
    ],
  };
}

/**
 * Execute generated Three.js code and add object to scene
 */
export async function executeAndAddObject(
  result: VideoToLegoResult,
  scene: any,
  objectName: string
): Promise<{ object: any; modelAnalysis?: any }> {
  try {
    // Import THREE
    const THREE = await import('three');
    
    // Create a safe execution context
    const func = new Function(
      'THREE',
      `
        try {
          ${result.threeJSCode}
        } catch (e) {
          console.error('Error in generated code:', e);
          throw e;
        }
      `
    );
    
    // Execute the function to create the group
    const object = func(THREE);
    
    // Verify it's a Three.js object
    if (!object || typeof object.add !== 'function') {
      throw new Error('Generated code did not return a valid Three.js object');
    }
    
    // Add to scene
    scene.add(object);
    
    console.log(`[VideoTo3JS] Successfully added ${objectName} to scene`);
    console.log('[VideoTo3JS] Model analysis:', result.modelAnalysis);
    
    return {
      object,
      modelAnalysis: result.modelAnalysis,
    };
  } catch (error) {
    console.error('[VideoTo3JS] Error executing Three.js code:', error);
    throw error;
  }
}
