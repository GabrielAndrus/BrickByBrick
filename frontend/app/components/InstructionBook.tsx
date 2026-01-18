'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { downloadLegoPDF } from '../../lib/legoPDFGenerator';
import { 
  getEnhancedInstructions, 
  type EnhancedManual, 
  type LegoStyleStep 
} from '../../lib/geminiLegoInstructions';

/**
 * InstructionBook Component
 * A LEGO-themed book-style flip viewer for building instructions
 * Features Gemini AI enhancement for authentic LEGO instruction style
 */

interface BuildStep {
  step_number: number;
  layer_z: number;
  bricks_in_step: Array<{
    part_id: string;
    lego_type?: string;
    position?: { studs?: number[] };
    rotation?: number;
    color_name?: string;
  }>;
  piece_counts: Record<string, number>;
  instructions: string;
}

interface PieceBreakdown {
  part_id: string;
  color_id: number;
  quantity: number;
  piece_name: string;
  color_name?: string;
  price_estimate?: number;
}

interface InstructionBookProps {
  projectName: string;
  manual: {
    total_steps: number;
    difficulty: string;
    estimated_time_minutes: number;
    baseplate?: {
      size_studs: number[];
      lego_type: string;
    };
    steps: BuildStep[];
    layer_summary: Record<number, string>;
  };
  pieceCount: {
    total_pieces: number;
    total_unique: number;
    breakdown: PieceBreakdown[];
    by_category?: Record<string, number>;
    by_color?: Record<string, number>;
    estimated_cost?: number;
  };
  isOpen: boolean;
  onClose: () => void;
}

// LEGO brick colors for visual elements
const BRICK_COLORS = [
  '#E3000B', // Red
  '#0055BF', // Blue
  '#237841', // Green
  '#FFCA28', // Yellow
  '#FF6B00', // Orange
  '#9C27B0', // Purple
  '#00BCD4', // Cyan
];

export default function InstructionBook({
  projectName,
  manual,
  pieceCount,
  isOpen,
  onClose,
}: InstructionBookProps) {
  const [currentPage, setCurrentPage] = useState(0);
  const [direction, setDirection] = useState(0);
  const [isFlipping, setIsFlipping] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  
  // Gemini enhancement state - uses env variable
  const geminiApiKey = process.env.NEXT_PUBLIC_GEMINI_API_KEY || '';
  const [useGemini, setUseGemini] = useState(!!geminiApiKey);
  const [enhancedManual, setEnhancedManual] = useState<EnhancedManual | null>(null);
  const [isEnhancing, setIsEnhancing] = useState(false);

  const totalPages = 2 + manual.total_steps; // cover + parts + steps
  const hasNoData = pieceCount.total_pieces === 0 && manual.total_steps === 0;

  // Load Gemini enhancements when enabled and API key is available
  useEffect(() => {
    if (useGemini && geminiApiKey && !enhancedManual && !isEnhancing && !hasNoData) {
      loadGeminiEnhancements();
    }
  }, [useGemini, geminiApiKey]);

  const loadGeminiEnhancements = async () => {
    if (!geminiApiKey) return;
    
    setIsEnhancing(true);
    try {
      const enhanced = await getEnhancedInstructions(
        manual,
        pieceCount,
        projectName,
        geminiApiKey
      );
      setEnhancedManual(enhanced);
      console.log('[Gemini] Enhanced instructions loaded!');
    } catch (error) {
      console.error('[Gemini] Failed to enhance instructions:', error);
    } finally {
      setIsEnhancing(false);
    }
  };

  // Download PDF handler
  const handleDownloadPDF = async () => {
    if (isDownloading) return;
    
    setIsDownloading(true);
    try {
      await downloadLegoPDF({
        projectName,
        manual,
        pieceCount,
        useGemini: useGemini && !!geminiApiKey,
        geminiApiKey,
      });
    } catch (error) {
      console.error('Failed to download PDF:', error);
    } finally {
      setIsDownloading(false);
    }
  };

  const nextPage = () => {
    if (currentPage < totalPages - 1 && !isFlipping) {
      setIsFlipping(true);
      setDirection(1);
      setCurrentPage(currentPage + 1);
      setTimeout(() => setIsFlipping(false), 600);
    }
  };

  const prevPage = () => {
    if (currentPage > 0 && !isFlipping) {
      setIsFlipping(true);
      setDirection(-1);
      setCurrentPage(currentPage - 1);
      setTimeout(() => setIsFlipping(false), 600);
    }
  };

  if (!isOpen) return null;

  // LEGO stud pattern for decorative elements
  const StudPattern = ({ count = 4, color = '#e3000b' }: { count?: number; color?: string }) => (
    <div className="flex gap-2 justify-center">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="w-4 h-4 rounded-full"
          style={{
            background: `linear-gradient(135deg, ${color} 0%, ${color} 50%, rgba(0,0,0,0.2) 100%)`,
            boxShadow: `inset -1px -1px 2px rgba(0,0,0,0.3), inset 1px 1px 2px rgba(255,255,255,0.3)`,
          }}
        />
      ))}
    </div>
  );

  // Brick callout component (like in real LEGO instructions)
  const BrickCallout = ({ partName, quantity, color }: { partName: string; quantity: number; color: string }) => (
    <div className="flex items-center gap-2 bg-white rounded-lg px-3 py-2 shadow-md border-2 border-gray-200">
      <div 
        className="w-8 h-6 rounded"
        style={{ backgroundColor: color }}
      />
      <span className="text-xs font-medium text-gray-700">{partName}</span>
      <span className="bg-black text-white text-xs font-bold px-2 py-0.5 rounded">
        {quantity}×
      </span>
    </div>
  );

  // Arrow indicator component
  const PlacementArrow = ({ number }: { number: number }) => (
    <div className="flex items-center gap-1">
      <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
        {number}
      </div>
      <svg width="20" height="12" viewBox="0 0 20 12" fill="none">
        <path d="M0 6H16M16 6L11 1M16 6L11 11" stroke="#0055BF" strokeWidth="2"/>
      </svg>
    </div>
  );

  const renderPageContent = () => {
    // Cover page
    if (currentPage === 0) {
      if (hasNoData) {
        return (
          <div className="h-full flex flex-col items-center justify-center p-12 text-center">
            <div className="text-8xl mb-6">🧱</div>
            <h1 className="text-3xl font-black mb-4">Nothing to Display</h1>
            <p className="text-lg mb-2">No environment has been loaded yet.</p>
            <p className="text-sm opacity-70">Upload a video to generate your LEGO build!</p>
          </div>
        );
      }

      return (
        <div className="h-full flex flex-col p-8">
          {/* LEGO Logo area */}
          <div className="text-center mb-4">
            <StudPattern count={6} color="#e3000b" />
          </div>

          {/* Title area */}
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            <div className="text-6xl mb-4">🏠</div>
            <h1 className="text-4xl font-black text-gray-900 mb-2">{projectName}</h1>
            
            {/* Gemini-enhanced tagline */}
            {enhancedManual?.cover_tagline ? (
              <p className="text-xl text-blue-600 font-semibold mb-4 italic">
                "{enhancedManual.cover_tagline}"
              </p>
            ) : (
              <p className="text-xl text-gray-600 mb-4">Building Instructions</p>
            )}

            {/* Stats grid - LEGO style */}
            <div className="grid grid-cols-2 gap-4 w-full max-w-sm mb-6">
              <div className="bg-red-600 text-white rounded-lg p-3 shadow-lg text-center">
                <p className="text-3xl font-black">{pieceCount.total_pieces}</p>
                <p className="text-xs opacity-90">PIECES</p>
              </div>
              <div className="bg-blue-600 text-white rounded-lg p-3 shadow-lg text-center">
                <p className="text-3xl font-black">{pieceCount.total_unique}</p>
                <p className="text-xs opacity-90">TYPES</p>
              </div>
              <div className="bg-green-600 text-white rounded-lg p-3 shadow-lg text-center">
                <p className="text-3xl font-black">{manual.total_steps}</p>
                <p className="text-xs opacity-90">STEPS</p>
              </div>
              <div className="bg-orange-500 text-white rounded-lg p-3 shadow-lg text-center">
                <p className="text-3xl font-black">{manual.estimated_time_minutes}m</p>
                <p className="text-xs opacity-90">TIME</p>
              </div>
            </div>

            {/* Difficulty */}
            <div className="flex gap-3 flex-wrap justify-center mb-4">
              <span className="px-4 py-2 bg-gray-900 text-white rounded-full text-sm font-bold">
                {manual.difficulty}
              </span>
              {enhancedManual?.difficulty_description && (
                <span className="px-4 py-2 bg-yellow-400 text-gray-900 rounded-full text-sm font-bold">
                  {enhancedManual.difficulty_description}
                </span>
              )}
            </div>

            {/* Gemini toggle */}
            {geminiApiKey && (
              <div className="w-full max-w-sm bg-gray-100 rounded-lg p-3 mt-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-700">✨ AI Enhancement</span>
                  <button
                    onClick={() => setUseGemini(!useGemini)}
                    disabled={isEnhancing}
                    className={`px-3 py-1 rounded-full text-xs font-bold transition-colors ${
                      useGemini 
                        ? 'bg-green-500 text-white' 
                        : 'bg-gray-300 text-gray-600'
                    }`}
                  >
                    {useGemini ? 'ON' : 'OFF'}
                  </button>
                </div>
                {isEnhancing && (
                  <p className="text-xs text-blue-600 mt-2">⏳ Enhancing with Gemini AI...</p>
                )}
                {enhancedManual && (
                  <p className="text-xs text-green-600 mt-2">✓ AI-enhanced instructions ready!</p>
                )}
              </div>
            )}
          </div>

          {/* Bottom */}
          <div className="text-center mt-4">
            <p className="text-sm text-gray-500 mb-2">→ to browse • 📥 to download PDF</p>
            <StudPattern count={6} color="#1e40af" />
          </div>
        </div>
      );
    }

    // Parts list page
    if (currentPage === 1) {
      return (
        <div className="h-full flex flex-col p-6">
          {/* Header */}
          <div className="flex items-center gap-4 mb-4 pb-3 border-b-4 border-red-600">
            <div className="w-12 h-12 bg-red-600 rounded-lg flex items-center justify-center text-white text-2xl">
              📦
            </div>
            <div>
              <h2 className="text-2xl font-black text-gray-900">Parts Required</h2>
              <p className="text-sm text-gray-500">Gather these before building</p>
            </div>
          </div>

          {/* Building tips from Gemini */}
          {enhancedManual?.building_tips && enhancedManual.building_tips.length > 0 && (
            <div className="bg-yellow-50 border-2 border-yellow-300 rounded-lg p-3 mb-4">
              <p className="text-sm font-bold text-yellow-800 mb-1">💡 Building Tips:</p>
              <ul className="text-xs text-yellow-700 list-disc list-inside">
                {enhancedManual.building_tips.slice(0, 3).map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Parts grid - LEGO manual style */}
          <div className="flex-1 overflow-y-auto">
            <div className="grid grid-cols-2 gap-2">
              {pieceCount.breakdown.slice(0, 16).map((part, idx) => (
                <BrickCallout
                  key={idx}
                  partName={part.piece_name}
                  quantity={part.quantity}
                  color={BRICK_COLORS[idx % BRICK_COLORS.length]}
                />
              ))}
            </div>
            {pieceCount.breakdown.length > 16 && (
              <p className="text-center text-gray-500 mt-3 text-sm">
                +{pieceCount.breakdown.length - 16} more types...
              </p>
            )}
          </div>

          {/* Total */}
          <div className="mt-3 pt-3 border-t-2 border-gray-200 flex justify-center">
            <div className="bg-black text-white px-6 py-2 rounded-full font-bold">
              Total: {pieceCount.total_pieces} pieces
            </div>
          </div>
        </div>
      );
    }

    // Build steps - LEGO instruction manual style
    const stepIndex = currentPage - 2;
    const step = manual.steps[stepIndex];
    const enhancedStep = enhancedManual?.steps[stepIndex];

    if (!step) {
      return (
        <div className="h-full flex items-center justify-center">
          <p className="text-gray-500">Step not found</p>
        </div>
      );
    }

    // Check if this is the baseplate step
    const isBaseplateStep = step.layer_z === -1;
    
    return (
      <div className="h-full flex flex-col p-6 bg-white">
        {/* Step header - LEGO style */}
        <div className="flex items-center gap-4 mb-4">
          <div className={`w-16 h-16 rounded-xl flex items-center justify-center text-white shadow-lg ${
            isBaseplateStep ? 'bg-green-600' : 'bg-blue-600'
          }`}>
            <span className="text-3xl font-black">{step.step_number}</span>
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-black text-gray-900">
              {isBaseplateStep 
                ? (enhancedStep?.title || "Place the Baseplate")
                : (enhancedStep?.title || `Step ${step.step_number}`)
              }
            </h2>
            <p className="text-sm text-gray-500">
              {isBaseplateStep ? "🟩 Foundation" : `Layer ${step.layer_z}`}
            </p>
          </div>
        </div>

        {/* Brick callouts - like real LEGO instructions */}
        <div className="bg-gray-50 rounded-xl p-4 mb-4 border-2 border-gray-200">
          <div className="flex flex-wrap gap-2 justify-center">
            {(enhancedStep?.brick_callouts || Object.entries(step.piece_counts).map(([id, qty]) => ({
              part_id: id,
              part_name: id,
              quantity: qty,
            }))).map((callout, idx) => (
              <div 
                key={idx}
                className="flex items-center gap-2 bg-white rounded-lg px-3 py-2 shadow border border-gray-100"
              >
                <div 
                  className="w-8 h-6 rounded flex items-center justify-center"
                  style={{ backgroundColor: BRICK_COLORS[idx % BRICK_COLORS.length] }}
                >
                  <span className="text-white text-xs">🧱</span>
                </div>
                <span className="text-xs font-medium">{callout.part_name}</span>
                <span className="bg-red-600 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                  {callout.quantity}×
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Visual instruction area - the main build visualization */}
        <div className="flex-1 bg-gray-100 rounded-xl p-4 mb-4 relative overflow-hidden">
          {/* Grid background like LEGO baseplates */}
          <div 
            className="absolute inset-0 opacity-10"
            style={{
              backgroundImage: 'radial-gradient(circle, #000 1px, transparent 1px)',
              backgroundSize: '16px 16px',
            }}
          />
          
          {/* Placement visualization */}
          <div className="relative z-10 h-full flex flex-col">
            {/* Instruction text - AI-enhanced or basic */}
            <div className="bg-white rounded-lg px-4 py-3 mb-3 shadow-sm border-l-4 border-blue-600">
              <p className="text-sm font-medium text-gray-800">
                {enhancedStep?.visual_instruction || step.instructions}
              </p>
            </div>

            {/* Placement arrows and guides */}
            <div className="flex-1 flex flex-wrap gap-3 items-start content-start">
              {step.bricks_in_step.slice(0, 8).map((brick, idx) => {
                const pos = brick.position?.studs || [0, 0, 0];
                return (
                  <div 
                    key={idx}
                    className="flex items-center gap-2 bg-white rounded-lg px-3 py-2 shadow-sm"
                  >
                    <PlacementArrow number={idx + 1} />
                    <div>
                      <p className="text-xs font-semibold text-gray-700">
                        {brick.lego_type || brick.part_id}
                      </p>
                      <p className="text-xs text-gray-500 font-mono">
                        Position: ({pos[0]}, {pos[1]})
                      </p>
                    </div>
                  </div>
                );
              })}
              {step.bricks_in_step.length > 8 && (
                <div className="text-xs text-gray-400 px-3 py-2">
                  +{step.bricks_in_step.length - 8} more...
                </div>
              )}
            </div>

            {/* AI-generated placement guide */}
            {enhancedStep?.placement_guide && enhancedStep.placement_guide.length > 0 && (
              <div className="mt-3">
                <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                  <p className="text-xs font-bold text-blue-800 mb-1">📍 Placement Guide:</p>
                  <ol className="text-xs text-blue-700 list-decimal list-inside space-y-1">
                    {enhancedStep.placement_guide.map((guide, i) => (
                      <li key={i}>{guide}</li>
                    ))}
                  </ol>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Tip from Gemini */}
        {enhancedStep?.tip && (
          <div className="bg-yellow-50 border-2 border-yellow-300 rounded-lg px-4 py-2">
            <p className="text-sm text-yellow-800">
              <strong>💡 Tip:</strong> {enhancedStep.tip}
            </p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      className="instruction-book-overlay"
      onClick={onClose}
    >
      {/* Book container */}
      <motion.div
        className="instruction-book-container"
        initial={{ scale: 0.8, opacity: 0, rotateX: 10 }}
        animate={{ scale: 1, opacity: 1, rotateX: 0 }}
        exit={{ scale: 0.8, opacity: 0, rotateX: -10 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Book spine */}
        <div className="instruction-book-spine">
          <div className="spine-decoration">
            <div className="spine-stud"></div>
            <div className="spine-stud"></div>
            <div className="spine-stud"></div>
            <div className="spine-title">LEGO</div>
            <div className="spine-stud"></div>
            <div className="spine-stud"></div>
            <div className="spine-stud"></div>
          </div>
        </div>

        {/* Main book area */}
        <div className="instruction-book-pages">
          {/* Page with flip animation */}
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentPage}
              custom={direction}
              initial={{ 
                rotateY: direction > 0 ? 90 : -90,
                opacity: 0,
              }}
              animate={{ 
                rotateY: 0,
                opacity: 1,
              }}
              exit={{ 
                rotateY: direction > 0 ? -90 : 90,
                opacity: 0,
              }}
              transition={{
                type: 'spring',
                stiffness: 300,
                damping: 30,
                opacity: { duration: 0.2 },
              }}
              className="instruction-book-page"
              style={{ transformStyle: 'preserve-3d' }}
            >
              {renderPageContent()}
            </motion.div>
          </AnimatePresence>

          {/* Page curl effect */}
          <div className="page-curl"></div>
        </div>

        {/* Navigation */}
        <div className="instruction-book-nav">
          <button
            onClick={prevPage}
            disabled={currentPage === 0 || isFlipping}
            className="nav-btn nav-prev"
          >
            ◀
          </button>

          <div className="page-indicator">
            <span className="current-page">{currentPage + 1}</span>
            <span className="separator">/</span>
            <span className="total-pages">{totalPages}</span>
          </div>

          <button
            onClick={nextPage}
            disabled={currentPage === totalPages - 1 || isFlipping}
            className="nav-btn nav-next"
          >
            ▶
          </button>
        </div>

        {/* Page label */}
        <div className="page-label">
          {currentPage === 0 
            ? 'Cover' 
            : currentPage === 1 
              ? 'Parts List' 
              : `Step ${currentPage - 1} of ${manual.total_steps}`
          }
        </div>

        {/* AI Enhancement indicator */}
        {enhancedManual && (
          <div className="absolute top-4 left-16 bg-gradient-to-r from-purple-500 to-blue-500 text-white px-3 py-1 rounded-full text-xs font-bold shadow-lg">
            ✨ AI Enhanced
          </div>
        )}

        {/* Download button */}
        <button 
          onClick={handleDownloadPDF} 
          disabled={isDownloading || hasNoData}
          className="instruction-book-download"
          title="Download PDF"
        >
          {isDownloading ? '⏳' : '📥'}
        </button>

        {/* Close button */}
        <button onClick={onClose} className="instruction-book-close">
          ✕
        </button>
      </motion.div>
    </div>
  );
}
