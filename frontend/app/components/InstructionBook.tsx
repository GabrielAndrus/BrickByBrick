'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * InstructionBook Component
 * A book-style flip viewer for LEGO building instructions
 * Includes piece count display and step-by-step navigation
 */

interface BuildStep {
  step_number: number;
  layer_z: number;
  bricks_in_step: Array<{
    part_id: string;
    lego_type?: string;
    position?: { studs?: number[] };
    rotation?: number;
  }>;
  piece_counts: Record<string, number>;
  instructions: string;
}

interface PieceBreakdown {
  part_id: string;
  color_id: number;
  quantity: number;
  piece_name: string;
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
  };
  isOpen: boolean;
  onClose: () => void;
}

// Page flip animation variants
const pageVariants = {
  enter: (direction: number) => ({
    rotateY: direction > 0 ? -90 : 90,
    opacity: 0,
    scale: 0.95,
  }),
  center: {
    rotateY: 0,
    opacity: 1,
    scale: 1,
  },
  exit: (direction: number) => ({
    rotateY: direction < 0 ? -90 : 90,
    opacity: 0,
    scale: 0.95,
  }),
};

export default function InstructionBook({
  projectName,
  manual,
  pieceCount,
  isOpen,
  onClose,
}: InstructionBookProps) {
  // Page 0 = cover, 1 = parts list, 2+ = build steps
  const [currentPage, setCurrentPage] = useState(0);
  const [direction, setDirection] = useState(0);

  const totalPages = 2 + manual.total_steps; // cover + parts + steps

  const nextPage = () => {
    if (currentPage < totalPages - 1) {
      setDirection(1);
      setCurrentPage(currentPage + 1);
    }
  };

  const prevPage = () => {
    if (currentPage > 0) {
      setDirection(-1);
      setCurrentPage(currentPage - 1);
    }
  };

  const goToPage = (page: number) => {
    setDirection(page > currentPage ? 1 : -1);
    setCurrentPage(page);
  };

  if (!isOpen) return null;

  // Check if there's no data to display
  const hasNoData = pieceCount.total_pieces === 0 && manual.total_steps === 0;

  const renderPageContent = () => {
    // Cover page
    if (currentPage === 0) {
      // Show "Nothing to display" if no environment loaded
      if (hasNoData) {
        return (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-gradient-to-b from-gray-500 to-gray-600 text-white rounded-r-lg">
            <div className="text-6xl mb-4">📭</div>
            <h1 className="text-2xl font-bold mb-2">Nothing to Display</h1>
            <p className="text-md opacity-90 mb-6">No environment has been loaded yet.</p>
            <p className="text-sm opacity-75">Upload or create an environment to see<br/>your LEGO build instructions here.</p>
          </div>
        );
      }

      return (
        <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-gradient-to-b from-red-600 to-red-700 text-white rounded-r-lg">
          <div className="text-6xl mb-4">🧱</div>
          <h1 className="text-3xl font-bold mb-2">{projectName}</h1>
          <p className="text-lg opacity-90 mb-6">LEGO Build Instructions</p>
          
          {/* LEGO Count Summary - First Page */}
          <div className="w-full mb-4">
            <p className="text-sm uppercase tracking-wider opacity-75 mb-2">Parts Summary</p>
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-sm bg-white/10 rounded-lg p-4 backdrop-blur">
            <div>
              <p className="text-2xl font-bold">{pieceCount.total_pieces}</p>
              <p className="opacity-75">Total Pieces</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{pieceCount.total_unique}</p>
              <p className="opacity-75">Unique Types</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{manual.total_steps}</p>
              <p className="opacity-75">Build Steps</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{manual.estimated_time_minutes}m</p>
              <p className="opacity-75">Est. Time</p>
            </div>
          </div>

          <div className="mt-6 px-4 py-2 bg-white/20 rounded-full text-sm">
            Difficulty: {manual.difficulty}
          </div>

          <p className="mt-8 text-sm opacity-75">Click → to start building</p>
        </div>
      );
    }

    // Parts list page
    if (currentPage === 1) {
      return (
        <div className="h-full flex flex-col p-6 bg-white rounded-r-lg overflow-hidden">
          <h2 className="text-xl font-bold text-gray-800 border-b-2 border-red-500 pb-2 mb-4">
            📦 Parts List
          </h2>
          
          <div className="flex-1 overflow-y-auto pr-2">
            <div className="grid gap-2">
              {pieceCount.breakdown.map((part, idx) => (
                <div 
                  key={idx} 
                  className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2 border border-gray-200"
                >
                  <div className="flex-1">
                    <p className="font-medium text-gray-800 text-sm">{part.piece_name}</p>
                    <p className="text-xs text-gray-500">ID: {part.part_id}</p>
                  </div>
                  <div className="bg-red-600 text-white px-3 py-1 rounded-full text-sm font-bold">
                    ×{part.quantity}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-200 text-center text-sm text-gray-600">
            Total: {pieceCount.total_pieces} pieces ({pieceCount.total_unique} unique types)
          </div>
        </div>
      );
    }

    // Build steps (page 2+)
    const stepIndex = currentPage - 2;
    const step = manual.steps[stepIndex];

    if (!step) {
      return (
        <div className="h-full flex items-center justify-center bg-white rounded-r-lg">
          <p className="text-gray-500">No step data available</p>
        </div>
      );
    }

    return (
      <div className="h-full flex flex-col p-6 bg-white rounded-r-lg overflow-hidden">
        {/* Step header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-lg px-4 py-3 mb-4">
          <h2 className="text-xl font-bold">Step {step.step_number}</h2>
          <p className="text-sm opacity-90">Layer {step.layer_z}</p>
        </div>

        {/* Parts for this step */}
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">🧱 Pieces needed:</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(step.piece_counts).map(([partId, qty]) => (
              <span 
                key={partId}
                className="inline-flex items-center bg-yellow-100 border border-yellow-300 rounded px-2 py-1 text-sm"
              >
                <span className="font-medium text-gray-700">{partId}</span>
                <span className="ml-1 text-yellow-700 font-bold">×{qty}</span>
              </span>
            ))}
          </div>
        </div>

        {/* Brick placements */}
        <div className="flex-1 overflow-y-auto">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">📍 Placement:</h3>
          <div className="grid gap-1 text-sm">
            {step.bricks_in_step.slice(0, 10).map((brick, idx) => {
              const pos = brick.position?.studs || [0, 0, 0];
              return (
                <div key={idx} className="flex items-center gap-2 bg-gray-50 rounded px-2 py-1">
                  <span className="w-5 h-5 bg-blue-500 text-white rounded-full text-xs flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <span className="text-gray-700">
                    {brick.part_id} at ({pos[0]}, {pos[1]})
                    {brick.rotation ? `, ${brick.rotation}°` : ''}
                  </span>
                </div>
              );
            })}
            {step.bricks_in_step.length > 10 && (
              <p className="text-gray-500 text-xs italic pl-7">
                +{step.bricks_in_step.length - 10} more bricks...
              </p>
            )}
          </div>
        </div>

        {/* Layer tip */}
        {manual.layer_summary[step.layer_z] && (
          <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
            💡 {manual.layer_summary[step.layer_z]}
          </div>
        )}
      </div>
    );
  };

  return (
    <motion.div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      {/* Book container */}
      <motion.div
        className="relative w-full max-w-md h-[600px] perspective-1000"
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.8, opacity: 0 }}
        transition={{ type: 'spring', damping: 25 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Book spine */}
        <div className="absolute left-0 top-0 bottom-0 w-4 bg-gradient-to-r from-gray-800 to-gray-700 rounded-l-lg shadow-lg" />
        
        {/* Page content with flip animation */}
        <div className="ml-4 h-full shadow-2xl rounded-r-lg overflow-hidden bg-white">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentPage}
              custom={direction}
              variants={pageVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{
                rotateY: { type: 'spring', stiffness: 300, damping: 30 },
                opacity: { duration: 0.2 },
              }}
              className="h-full"
              style={{ transformStyle: 'preserve-3d' }}
            >
              {renderPageContent()}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Navigation controls */}
        <div className="absolute -bottom-16 left-1/2 -translate-x-1/2 flex items-center gap-4">
          <button
            onClick={prevPage}
            disabled={currentPage === 0}
            className="w-10 h-10 rounded-full bg-white shadow-lg flex items-center justify-center text-gray-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-100 transition-colors"
          >
            ←
          </button>

          {/* Page dots */}
          <div className="flex gap-1">
            {Array.from({ length: Math.min(totalPages, 10) }).map((_, i) => (
              <button
                key={i}
                onClick={() => goToPage(i)}
                className={`w-2 h-2 rounded-full transition-all ${
                  i === currentPage 
                    ? 'bg-red-500 scale-125' 
                    : 'bg-white/70 hover:bg-white'
                }`}
              />
            ))}
            {totalPages > 10 && (
              <span className="text-white/70 text-xs ml-1">+{totalPages - 10}</span>
            )}
          </div>

          <button
            onClick={nextPage}
            disabled={currentPage === totalPages - 1}
            className="w-10 h-10 rounded-full bg-white shadow-lg flex items-center justify-center text-gray-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-100 transition-colors"
          >
            →
          </button>
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-white shadow-lg flex items-center justify-center text-gray-600 hover:bg-gray-100 transition-colors"
        >
          ✕
        </button>

        {/* Page number */}
        <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 text-white/80 text-sm">
          {currentPage === 0 ? 'Cover' : currentPage === 1 ? 'Parts List' : `Step ${currentPage - 1} of ${manual.total_steps}`}
        </div>
      </motion.div>
    </motion.div>
  );
}
