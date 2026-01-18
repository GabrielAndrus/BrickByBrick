/**
 * LEGO Instruction Manual PDF Generator
 * Creates authentic LEGO-style instruction manuals with Gemini AI enhancement
 */

import jsPDF from 'jspdf';
import type { InstructionManual, PieceCount } from './legoManualGenerator';

// LEGO Brand Colors
const LEGO_COLORS = {
  red: '#E3000B',
  yellow: '#FFCA28',
  blue: '#0055BF',
  green: '#237841',
  black: '#1B1B1B',
  white: '#FFFFFF',
  lightGray: '#A0A5A9',
  darkGray: '#6D6E6C',
};

// Part ID to visual representation
const BRICK_VISUALS: Record<string, { symbol: string; width: number; height: number }> = {
  '3001': { symbol: '▬▬', width: 4, height: 2 },
  '3002': { symbol: '▬▬', width: 3, height: 2 },
  '3003': { symbol: '▪▪', width: 2, height: 2 },
  '3004': { symbol: '▪', width: 2, height: 1 },
  '3005': { symbol: '•', width: 1, height: 1 },
  '3009': { symbol: '▬▬▬', width: 6, height: 1 },
  '3010': { symbol: '▬▬', width: 4, height: 1 },
  '3068': { symbol: '□', width: 2, height: 2 },
  '3069': { symbol: '▭', width: 2, height: 1 },
  '3070': { symbol: '○', width: 1, height: 1 },
};

interface GeneratorOptions {
  projectName: string;
  manual: InstructionManual;
  pieceCount: PieceCount;
  useGemini?: boolean;
  geminiApiKey?: string;
}

/**
 * Generate enhanced descriptions using Gemini AI
 */
async function enhanceWithGemini(
  step: InstructionManual['steps'][0],
  apiKey: string
): Promise<string> {
  try {
    const { GoogleGenerativeAI } = await import('@google/generative-ai');
    const genAI = new GoogleGenerativeAI(apiKey);
    const model = genAI.getGenerativeModel({ model: 'gemini-pro' });

    const prompt = `You are writing instructions for a LEGO building manual. Write a brief, clear instruction (1-2 sentences max) for this building step:
    
Step ${step.step_number}: Layer ${step.layer_z}
Pieces needed: ${JSON.stringify(step.piece_counts)}
Number of bricks to place: ${step.bricks_in_step.length}

Write in the style of official LEGO instructions - simple, clear, kid-friendly. Focus on what the builder is creating at this stage.`;

    const result = await model.generateContent(prompt);
    const response = await result.response;
    return response.text() || step.instructions;
  } catch (error) {
    console.error('Gemini enhancement failed:', error);
    return step.instructions;
  }
}

/**
 * Draw a LEGO stud pattern
 */
function drawStudPattern(
  pdf: jsPDF,
  x: number,
  y: number,
  count: number,
  color: string = LEGO_COLORS.red
) {
  const studSize = 4;
  const spacing = 6;
  
  for (let i = 0; i < count; i++) {
    pdf.setFillColor(color);
    pdf.circle(x + i * spacing, y, studSize / 2, 'F');
    // Inner highlight
    pdf.setFillColor('#FFFFFF');
    pdf.circle(x + i * spacing - 0.5, y - 0.5, studSize / 4, 'F');
  }
}

/**
 * Draw a simplified LEGO brick icon
 */
function drawBrickIcon(
  pdf: jsPDF,
  x: number,
  y: number,
  width: number,
  height: number,
  color: string
) {
  const brickWidth = width * 8;
  const brickHeight = height * 6;
  
  // Main brick body
  pdf.setFillColor(color);
  pdf.roundedRect(x, y, brickWidth, brickHeight, 1, 1, 'F');
  
  // Top studs
  pdf.setFillColor(color);
  const studSize = 3;
  for (let i = 0; i < width; i++) {
    for (let j = 0; j < height; j++) {
      const studX = x + 4 + i * 8;
      const studY = y - 2;
      pdf.circle(studX, studY, studSize / 2, 'F');
    }
  }
  
  // Outline
  pdf.setDrawColor('#000000');
  pdf.setLineWidth(0.3);
  pdf.roundedRect(x, y, brickWidth, brickHeight, 1, 1, 'S');
}

/**
 * Generate LEGO-style instruction manual PDF
 */
export async function generateLegoPDF(options: GeneratorOptions): Promise<Blob> {
  const { projectName, manual, pieceCount, useGemini = false, geminiApiKey } = options;
  
  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 15;
  const contentWidth = pageWidth - 2 * margin;

  // ===== COVER PAGE =====
  // Background
  pdf.setFillColor(LEGO_COLORS.yellow);
  pdf.rect(0, 0, pageWidth, pageHeight, 'F');
  
  // Top red banner
  pdf.setFillColor(LEGO_COLORS.red);
  pdf.rect(0, 0, pageWidth, 40, 'F');
  
  // LEGO-style title
  pdf.setFillColor(LEGO_COLORS.yellow);
  pdf.roundedRect(margin, 25, contentWidth, 30, 3, 3, 'F');
  pdf.setDrawColor('#000000');
  pdf.setLineWidth(1);
  pdf.roundedRect(margin, 25, contentWidth, 30, 3, 3, 'S');
  
  pdf.setFont('helvetica', 'bold');
  pdf.setFontSize(24);
  pdf.setTextColor('#000000');
  pdf.text('BUILDING INSTRUCTIONS', pageWidth / 2, 44, { align: 'center' });
  
  // Project name
  pdf.setFontSize(32);
  pdf.setTextColor(LEGO_COLORS.red);
  pdf.text(projectName.toUpperCase(), pageWidth / 2, 90, { align: 'center' });
  
  // Decorative studs
  drawStudPattern(pdf, pageWidth / 2 - 15, 110, 6, LEGO_COLORS.red);
  
  // Stats boxes
  const boxWidth = 40;
  const boxHeight = 35;
  const boxY = 130;
  const boxSpacing = 10;
  const startX = (pageWidth - (4 * boxWidth + 3 * boxSpacing)) / 2;
  
  const stats = [
    { value: pieceCount.total_pieces, label: 'PIECES', color: LEGO_COLORS.red },
    { value: pieceCount.total_unique, label: 'TYPES', color: LEGO_COLORS.blue },
    { value: manual.total_steps, label: 'STEPS', color: LEGO_COLORS.green },
    { value: `${manual.estimated_time_minutes}m`, label: 'TIME', color: '#FF6B00' },
  ];
  
  stats.forEach((stat, i) => {
    const x = startX + i * (boxWidth + boxSpacing);
    pdf.setFillColor(stat.color);
    pdf.roundedRect(x, boxY, boxWidth, boxHeight, 2, 2, 'F');
    pdf.setDrawColor('#000000');
    pdf.setLineWidth(0.5);
    pdf.roundedRect(x, boxY, boxWidth, boxHeight, 2, 2, 'S');
    
    pdf.setFontSize(18);
    pdf.setTextColor('#FFFFFF');
    pdf.text(String(stat.value), x + boxWidth / 2, boxY + 15, { align: 'center' });
    pdf.setFontSize(8);
    pdf.text(stat.label, x + boxWidth / 2, boxY + 25, { align: 'center' });
  });
  
  // Difficulty badge
  pdf.setFillColor('#000000');
  pdf.roundedRect(pageWidth / 2 - 25, 185, 50, 15, 2, 2, 'F');
  pdf.setFontSize(10);
  pdf.setTextColor('#FFFFFF');
  pdf.text(manual.difficulty.toUpperCase(), pageWidth / 2, 195, { align: 'center' });
  
  // Bottom decoration
  pdf.setFillColor(LEGO_COLORS.red);
  pdf.rect(0, pageHeight - 20, pageWidth, 20, 'F');
  drawStudPattern(pdf, pageWidth / 2 - 20, pageHeight - 10, 8, LEGO_COLORS.yellow);
  
  // ===== PARTS LIST PAGE =====
  pdf.addPage();
  
  // Header
  pdf.setFillColor(LEGO_COLORS.blue);
  pdf.rect(0, 0, pageWidth, 25, 'F');
  pdf.setFontSize(16);
  pdf.setTextColor('#FFFFFF');
  pdf.text('PARTS LIST', pageWidth / 2, 16, { align: 'center' });
  
  // Parts grid
  let yPos = 35;
  const colWidth = contentWidth / 3;
  let col = 0;
  
  pdf.setFontSize(9);
  
  for (const part of pieceCount.breakdown.slice(0, 24)) {
    const x = margin + col * colWidth;
    
    // Part box
    pdf.setFillColor('#F5F5F5');
    pdf.roundedRect(x, yPos, colWidth - 5, 18, 2, 2, 'F');
    pdf.setDrawColor('#CCCCCC');
    pdf.setLineWidth(0.3);
    pdf.roundedRect(x, yPos, colWidth - 5, 18, 2, 2, 'S');
    
    // Part icon placeholder
    const brickInfo = BRICK_VISUALS[part.part_id] || { symbol: '▪', width: 2, height: 1 };
    pdf.setFillColor(LEGO_COLORS.red);
    pdf.roundedRect(x + 2, yPos + 3, 12, 12, 1, 1, 'F');
    
    // Part name and quantity
    pdf.setTextColor('#000000');
    pdf.setFont('helvetica', 'normal');
    pdf.text(part.piece_name.substring(0, 12), x + 18, yPos + 8);
    
    // Quantity badge
    pdf.setFillColor(LEGO_COLORS.red);
    pdf.circle(x + colWidth - 12, yPos + 9, 5, 'F');
    pdf.setTextColor('#FFFFFF');
    pdf.setFont('helvetica', 'bold');
    pdf.text(String(part.quantity), x + colWidth - 12, yPos + 11, { align: 'center' });
    
    col++;
    if (col >= 3) {
      col = 0;
      yPos += 22;
    }
    
    if (yPos > pageHeight - 40) break;
  }
  
  // Total at bottom
  pdf.setFillColor(LEGO_COLORS.yellow);
  pdf.rect(0, pageHeight - 25, pageWidth, 25, 'F');
  pdf.setFontSize(12);
  pdf.setTextColor('#000000');
  pdf.setFont('helvetica', 'bold');
  pdf.text(`TOTAL: ${pieceCount.total_pieces} pieces`, pageWidth / 2, pageHeight - 10, { align: 'center' });

  // ===== BUILD STEPS =====
  for (let i = 0; i < manual.steps.length; i++) {
    const step = manual.steps[i];
    
    // Add new page for each step (2 steps per page for efficiency)
    if (i % 2 === 0) {
      pdf.addPage();
    }
    
    const isTopHalf = i % 2 === 0;
    const startY = isTopHalf ? 10 : pageHeight / 2 + 5;
    const halfHeight = pageHeight / 2 - 15;
    
    // Step number circle
    pdf.setFillColor(LEGO_COLORS.blue);
    pdf.circle(margin + 12, startY + 12, 10, 'F');
    pdf.setFontSize(14);
    pdf.setTextColor('#FFFFFF');
    pdf.setFont('helvetica', 'bold');
    pdf.text(String(step.step_number), margin + 12, startY + 16, { align: 'center' });
    
    // Layer indicator
    pdf.setFillColor('#F0F0F0');
    pdf.roundedRect(margin + 28, startY + 5, 35, 14, 2, 2, 'F');
    pdf.setFontSize(8);
    pdf.setTextColor('#666666');
    pdf.text(`Layer ${step.layer_z}`, margin + 45, startY + 14, { align: 'center' });
    
    // Parts needed for this step
    const partsY = startY + 25;
    pdf.setFillColor(LEGO_COLORS.yellow);
    pdf.roundedRect(margin, partsY, contentWidth, 25, 2, 2, 'F');
    pdf.setDrawColor('#000000');
    pdf.setLineWidth(0.5);
    pdf.roundedRect(margin, partsY, contentWidth, 25, 2, 2, 'S');
    
    // Draw parts icons
    let partX = margin + 5;
    const partEntries = Object.entries(step.piece_counts).slice(0, 6);
    
    for (const [partId, qty] of partEntries) {
      // Small brick icon
      pdf.setFillColor(LEGO_COLORS.red);
      pdf.roundedRect(partX, partsY + 5, 15, 10, 1, 1, 'F');
      
      // Quantity
      pdf.setFillColor('#000000');
      pdf.circle(partX + 20, partsY + 10, 4, 'F');
      pdf.setFontSize(7);
      pdf.setTextColor('#FFFFFF');
      pdf.text(`×${qty}`, partX + 20, partsY + 12, { align: 'center' });
      
      partX += 30;
    }
    
    // Main building area
    const buildAreaY = partsY + 30;
    const buildAreaHeight = halfHeight - 50;
    
    pdf.setFillColor('#FAFAFA');
    pdf.roundedRect(margin, buildAreaY, contentWidth, buildAreaHeight, 3, 3, 'F');
    pdf.setDrawColor('#E0E0E0');
    pdf.setLineWidth(0.5);
    pdf.roundedRect(margin, buildAreaY, contentWidth, buildAreaHeight, 3, 3, 'S');
    
    // Visual representation of brick placements (simplified grid)
    const gridSize = 8;
    const gridStartX = margin + 20;
    const gridStartY = buildAreaY + 15;
    
    // Draw placement indicators for first few bricks
    step.bricks_in_step.slice(0, 8).forEach((brick, idx) => {
      const pos = brick.position?.studs || [0, 0, 0];
      const brickX = gridStartX + (idx % 4) * 40;
      const brickY = gridStartY + Math.floor(idx / 4) * 25;
      
      // Brick representation
      pdf.setFillColor(LEGO_COLORS.red);
      pdf.roundedRect(brickX, brickY, 25, 15, 2, 2, 'F');
      
      // Position label
      pdf.setFontSize(6);
      pdf.setTextColor('#666666');
      pdf.text(`(${pos[0]},${pos[1]})`, brickX + 12, brickY + 22, { align: 'center' });
    });
    
    // Instruction text
    let instructionText = step.instructions;
    
    // If Gemini is enabled, enhance the instruction
    if (useGemini && geminiApiKey) {
      instructionText = await enhanceWithGemini(step, geminiApiKey);
    }
    
    pdf.setFontSize(9);
    pdf.setTextColor('#333333');
    pdf.setFont('helvetica', 'normal');
    const textY = buildAreaY + buildAreaHeight - 10;
    const splitText = pdf.splitTextToSize(instructionText, contentWidth - 10);
    pdf.text(splitText.slice(0, 2), margin + 5, textY);
    
    // Divider line between steps
    if (!isTopHalf || i === manual.steps.length - 1) {
      pdf.setDrawColor('#CCCCCC');
      pdf.setLineWidth(0.3);
      pdf.line(margin, pageHeight / 2, pageWidth - margin, pageHeight / 2);
    }
  }
  
  // ===== COMPLETION PAGE =====
  pdf.addPage();
  
  pdf.setFillColor(LEGO_COLORS.green);
  pdf.rect(0, 0, pageWidth, pageHeight, 'F');
  
  // Congratulations
  pdf.setFillColor(LEGO_COLORS.yellow);
  pdf.roundedRect(margin, 60, contentWidth, 50, 5, 5, 'F');
  pdf.setDrawColor('#000000');
  pdf.setLineWidth(2);
  pdf.roundedRect(margin, 60, contentWidth, 50, 5, 5, 'S');
  
  pdf.setFontSize(28);
  pdf.setTextColor('#000000');
  pdf.setFont('helvetica', 'bold');
  pdf.text('COMPLETE!', pageWidth / 2, 92, { align: 'center' });
  
  // Trophy/celebration icon (using circles for studs pattern)
  drawStudPattern(pdf, pageWidth / 2 - 25, 130, 10, LEGO_COLORS.yellow);
  drawStudPattern(pdf, pageWidth / 2 - 20, 145, 8, LEGO_COLORS.red);
  drawStudPattern(pdf, pageWidth / 2 - 15, 160, 6, LEGO_COLORS.blue);
  
  // Stats summary
  pdf.setFillColor('#FFFFFF');
  pdf.roundedRect(margin + 20, 180, contentWidth - 40, 60, 3, 3, 'F');
  
  pdf.setFontSize(12);
  pdf.setTextColor('#333333');
  pdf.text(`You used ${pieceCount.total_pieces} pieces!`, pageWidth / 2, 200, { align: 'center' });
  pdf.text(`Completed ${manual.total_steps} building steps!`, pageWidth / 2, 215, { align: 'center' });
  pdf.text(`Great job building your ${projectName}!`, pageWidth / 2, 230, { align: 'center' });
  
  // Bottom decoration
  pdf.setFillColor(LEGO_COLORS.red);
  pdf.rect(0, pageHeight - 30, pageWidth, 30, 'F');
  
  pdf.setFontSize(10);
  pdf.setTextColor('#FFFFFF');
  pdf.text('Generated by Brick by Brick', pageWidth / 2, pageHeight - 12, { align: 'center' });
  
  // Return as blob
  return pdf.output('blob');
}

/**
 * Download the PDF
 */
export async function downloadLegoPDF(options: GeneratorOptions): Promise<void> {
  const blob = await generateLegoPDF(options);
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${options.projectName.replace(/\s+/g, '_')}_Instructions.pdf`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
