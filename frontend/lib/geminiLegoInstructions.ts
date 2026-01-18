/**
 * Gemini LEGO Instructions Generator
 * Uses Google Gemini AI to create authentic LEGO-style building instructions
 */

import type { InstructionManual, PieceCount } from './legoManualGenerator';

// LEGO Part names for better descriptions
const PART_NAMES: Record<string, string> = {
  '3001': '2×4 Brick',
  '3002': '2×3 Brick',
  '3003': '2×2 Brick',
  '3004': '1×2 Brick',
  '3005': '1×1 Brick',
  '3009': '1×6 Brick',
  '3010': '1×4 Brick',
  '3622': '1×3 Brick',
  '3068': '2×2 Tile',
  '3069': '1×2 Tile',
  '3070': '1×1 Tile',
  '3024': '1×1 Plate',
  '3023': '1×2 Plate',
  '3022': '2×2 Plate',
  '3020': '2×4 Plate',
};

export interface LegoStyleStep {
  step_number: number;
  layer_z: number;
  title: string;
  visual_instruction: string;
  placement_guide: string[];
  tip?: string;
  brick_callouts: Array<{
    part_id: string;
    part_name: string;
    quantity: number;
    color?: string;
  }>;
  arrows: Array<{
    from: string;
    to: string;
    label?: string;
  }>;
}

export interface EnhancedManual {
  project_name: string;
  cover_tagline: string;
  difficulty_description: string;
  steps: LegoStyleStep[];
  completion_message: string;
  building_tips: string[];
}

/**
 * Generate LEGO-style instructions using Gemini
 */
export async function generateLegoInstructions(
  manual: InstructionManual,
  pieceCount: PieceCount,
  projectName: string,
  apiKey: string
): Promise<EnhancedManual> {
  const { GoogleGenerativeAI } = await import('@google/generative-ai');
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({ model: 'gemini-pro' });

  // Generate cover and overall content
  const coverPrompt = `You are creating a LEGO instruction manual for a build called "${projectName}".

Build Stats:
- Total pieces: ${pieceCount.total_pieces}
- Unique piece types: ${pieceCount.total_unique}
- Total build steps: ${manual.total_steps}
- Difficulty: ${manual.difficulty}
- Estimated time: ${manual.estimated_time_minutes} minutes

Generate the following in JSON format:
{
  "cover_tagline": "A short, exciting tagline for the cover (like 'Build Your Dream Room!')",
  "difficulty_description": "A kid-friendly description of the difficulty level",
  "completion_message": "A celebratory message for when they finish building",
  "building_tips": ["3-4 general LEGO building tips for this project"]
}

Make it sound like official LEGO instructions - fun, encouraging, and kid-friendly.`;

  let coverData = {
    cover_tagline: "Build Your Dream Space!",
    difficulty_description: "A fun build for all ages!",
    completion_message: "Congratulations! You did it!",
    building_tips: [
      "Sort your pieces by color before starting",
      "Work on a flat, clean surface",
      "Follow each step carefully",
    ],
  };

  try {
    const coverResult = await model.generateContent(coverPrompt);
    const coverText = coverResult.response.text();
    const jsonMatch = coverText.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      coverData = JSON.parse(jsonMatch[0]);
    }
  } catch (e) {
    console.error('Failed to generate cover content:', e);
  }

  // Generate enhanced steps
  const enhancedSteps: LegoStyleStep[] = [];

  for (const step of manual.steps) {
    const partsList = Object.entries(step.piece_counts)
      .map(([id, qty]) => `${qty}× ${PART_NAMES[id] || `Part ${id}`}`)
      .join(', ');

    const stepPrompt = `You are writing Step ${step.step_number} of a LEGO instruction manual.

This step information:
- Layer/Level: ${step.layer_z}
- Pieces to add: ${partsList}
- Number of brick placements: ${step.bricks_in_step.length}

Brick positions (x, y coordinates on baseplate):
${step.bricks_in_step.slice(0, 8).map((b, i) => 
  `${i + 1}. ${PART_NAMES[b.part_id] || b.part_id} at position (${b.position?.studs?.[0] || 0}, ${b.position?.studs?.[1] || 0})`
).join('\n')}

Generate LEGO-style instruction content in JSON format:
{
  "title": "A short title for this step (e.g., 'Add the floor tiles', 'Build the desk base')",
  "visual_instruction": "One clear sentence describing what the builder is creating in this step",
  "placement_guide": ["2-3 short placement instructions like 'Place the 2×4 brick at the front left corner'"],
  "tip": "Optional helpful tip for this step (or null if not needed)"
}

Write in LEGO instruction style:
- Simple, clear language a child can understand
- Focus on WHAT is being built, not just WHERE bricks go
- Use spatial terms like "front", "back", "left corner", "center"
- Be encouraging and positive`;

    let stepData: {
      title: string;
      visual_instruction: string;
      placement_guide: string[];
      tip?: string;
    } = {
      title: `Step ${step.step_number}`,
      visual_instruction: step.instructions,
      placement_guide: [`Place ${step.bricks_in_step.length} bricks at layer ${step.layer_z}`],
    };

    try {
      const stepResult = await model.generateContent(stepPrompt);
      const stepText = stepResult.response.text();
      const jsonMatch = stepText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        stepData = JSON.parse(jsonMatch[0]);
      }
    } catch (e) {
      console.error(`Failed to generate step ${step.step_number}:`, e);
    }

    // Build brick callouts
    const brickCallouts = Object.entries(step.piece_counts).map(([partId, quantity]) => ({
      part_id: partId,
      part_name: PART_NAMES[partId] || `Part ${partId}`,
      quantity,
    }));

    // Generate arrow indicators for key placements
    const arrows = step.bricks_in_step.slice(0, 3).map((brick, i) => ({
      from: `piece-${i + 1}`,
      to: `pos-${brick.position?.studs?.[0] || 0}-${brick.position?.studs?.[1] || 0}`,
      label: `${i + 1}`,
    }));

    enhancedSteps.push({
      step_number: step.step_number,
      layer_z: step.layer_z,
      title: stepData.title,
      visual_instruction: stepData.visual_instruction,
      placement_guide: stepData.placement_guide,
      tip: stepData.tip,
      brick_callouts: brickCallouts,
      arrows,
    });
  }

  return {
    project_name: projectName,
    cover_tagline: coverData.cover_tagline,
    difficulty_description: coverData.difficulty_description,
    steps: enhancedSteps,
    completion_message: coverData.completion_message,
    building_tips: coverData.building_tips,
  };
}

/**
 * Generate a single step's LEGO-style instruction (for real-time use)
 */
export async function enhanceStepWithGemini(
  step: InstructionManual['steps'][0],
  stepContext: { projectName: string; totalSteps: number },
  apiKey: string
): Promise<LegoStyleStep> {
  const { GoogleGenerativeAI } = await import('@google/generative-ai');
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({ model: 'gemini-pro' });

  const partsList = Object.entries(step.piece_counts)
    .map(([id, qty]) => `${qty}× ${PART_NAMES[id] || `Part ${id}`}`)
    .join(', ');

  const prompt = `Create a LEGO instruction manual step for "${stepContext.projectName}".

Step ${step.step_number} of ${stepContext.totalSteps}:
- Layer: ${step.layer_z}
- Pieces: ${partsList}
- Placements: ${step.bricks_in_step.length}

Write like official LEGO instructions - minimal text, clear visuals description.

Respond with JSON:
{
  "title": "Short descriptive title",
  "visual_instruction": "What the builder is creating",
  "placement_guide": ["Placement instruction 1", "Placement instruction 2"],
  "tip": "Optional helpful tip or null"
}`;

  try {
    const result = await model.generateContent(prompt);
    const text = result.response.text();
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    
    if (jsonMatch) {
      const data = JSON.parse(jsonMatch[0]);
      return {
        step_number: step.step_number,
        layer_z: step.layer_z,
        title: data.title,
        visual_instruction: data.visual_instruction,
        placement_guide: data.placement_guide,
        tip: data.tip,
        brick_callouts: Object.entries(step.piece_counts).map(([partId, quantity]) => ({
          part_id: partId,
          part_name: PART_NAMES[partId] || `Part ${partId}`,
          quantity,
        })),
        arrows: [],
      };
    }
  } catch (e) {
    console.error('Gemini enhancement failed:', e);
  }

  // Fallback
  return {
    step_number: step.step_number,
    layer_z: step.layer_z,
    title: `Step ${step.step_number}`,
    visual_instruction: step.instructions,
    placement_guide: [`Add ${step.bricks_in_step.length} pieces`],
    brick_callouts: Object.entries(step.piece_counts).map(([partId, quantity]) => ({
      part_id: partId,
      part_name: PART_NAMES[partId] || `Part ${partId}`,
      quantity,
    })),
    arrows: [],
  };
}

/**
 * Cache for enhanced instructions
 */
const enhancedCache = new Map<string, EnhancedManual>();

/**
 * Get or generate enhanced instructions with caching
 */
export async function getEnhancedInstructions(
  manual: InstructionManual,
  pieceCount: PieceCount,
  projectName: string,
  apiKey: string
): Promise<EnhancedManual> {
  const cacheKey = `${projectName}-${manual.total_steps}`;
  
  if (enhancedCache.has(cacheKey)) {
    return enhancedCache.get(cacheKey)!;
  }

  const enhanced = await generateLegoInstructions(manual, pieceCount, projectName, apiKey);
  enhancedCache.set(cacheKey, enhanced);
  
  return enhanced;
}
