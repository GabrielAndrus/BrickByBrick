'use client';

import React, { useState } from 'react';

/**
 * Instruction Manual Component
 * Displays LEGO building instructions step-by-step
 */
interface BuildStep {
  step_number: number;
  layer_z: number;
  bricks_in_step: Array<{ part_id: string; lego_type: string; quantity: number }>;
  piece_counts: Record<string, number>;
  instructions: string;
}

interface BaseplateInfo {
  size_studs: number[];
  size_mm: number[];
  part_id: string;
  lego_type: string;
  color_id: number;
  quantity: number;
}

interface InstructionManualData {
  total_steps: number;
  difficulty: string;
  estimated_time_minutes: number;
  baseplate: BaseplateInfo;
  steps: BuildStep[];
  layer_summary: Record<number, string>;
}

interface InstructionManualProps {
  manual: InstructionManualData;
  projectName: string;
  totalBricks: number;
  pieceCounts: {
    total_pieces: number;
    total_unique: number;
    breakdown: Array<{
      part_id: string;
      color_id: number;
      quantity: number;
      piece_name: string;
    }>;
  };
}

export default function InstructionManual({
  manual,
  projectName,
  totalBricks,
  pieceCounts,
}: InstructionManualProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [showParts, setShowParts] = useState(true);
  const [showInstructions, setShowInstructions] = useState(true);

  const step = manual.steps[currentStep];

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6 border-b-2 border-blue-500 pb-4">
        <h1 className="text-3xl font-bold text-gray-800">{projectName}</h1>
        <p className="text-gray-600 mt-2">
          LEGO Instruction Manual • {pieceCounts.total_pieces} Pieces • Difficulty: {manual.difficulty}
        </p>
        <div className="mt-3 flex gap-4 text-sm">
          <span className="bg-blue-100 px-3 py-1 rounded">
            ⏱️ {manual.estimated_time_minutes} mins
          </span>
          <span className="bg-green-100 px-3 py-1 rounded">
            🧱 {pieceCounts.total_unique} Unique Types
          </span>
        </div>
      </div>

      {/* Baseplate Information */}
      <div className="mb-6 bg-yellow-50 border-2 border-yellow-300 rounded-lg p-4">
        <h2 className="font-bold text-lg mb-2">🏗️ Foundation (Step 0)</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-semibold text-gray-700">Baseplate Required:</p>
            <p className="text-lg font-bold text-gray-900">{manual.baseplate.lego_type}</p>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-700">Size:</p>
            <p className="text-lg font-bold text-gray-900">
              {manual.baseplate.size_studs[0]} × {manual.baseplate.size_studs[1]} studs
            </p>
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-2 italic">
          Place this flat baseplate first. All bricks will build on top of this foundation.
        </p>
      </div>

      {/* Parts List Toggle */}
      <div className="mb-6">
        <button
          onClick={() => setShowParts(!showParts)}
          className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded flex items-center justify-between"
        >
          <span>📦 Required Parts ({pieceCounts.total_unique} types)</span>
          <span className="text-xl">{showParts ? '▼' : '▶'}</span>
        </button>

        {showParts && (
          <div className="mt-4 bg-gray-50 rounded-lg p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-80 overflow-y-auto">
              {pieceCounts.breakdown.map((part, idx) => (
                <div key={idx} className="bg-white p-3 rounded border border-gray-200">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-semibold text-gray-800">{part.piece_name}</p>
                      <p className="text-xs text-gray-500">Part ID: {part.part_id}</p>
                    </div>
                    <span className="bg-blue-500 text-white px-3 py-1 rounded font-bold text-lg">
                      ×{part.quantity}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-sm text-gray-600 mt-3 italic">
              Total: {pieceCounts.total_pieces} pieces
            </p>
          </div>
        )}
      </div>

      {/* Step Display */}
      <div className="mb-6">
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-t-lg p-4">
          <h2 className="text-2xl font-bold">
            Step {step.step_number} / {manual.total_steps}
          </h2>
          <p className="text-blue-100 text-sm mt-1">Layer {step.layer_z}</p>
        </div>

        <div className="bg-white border border-t-0 border-gray-300 rounded-b-lg p-6">
          {/* Instructions Toggle */}
          <button
            onClick={() => setShowInstructions(!showInstructions)}
            className="w-full mb-4 bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold py-2 px-4 rounded flex items-center justify-between"
          >
            <span>📋 Instructions</span>
            <span className="text-xl">{showInstructions ? '▼' : '▶'}</span>
          </button>

          {showInstructions && (
            <div className="mb-4 p-4 bg-yellow-50 border-l-4 border-yellow-500 rounded">
              <p className="text-gray-800 leading-relaxed text-lg">
                {step.instructions}
              </p>
            </div>
          )}

          {/* Bricks for this step */}
          <div className="mb-4">
            <h3 className="font-bold text-lg text-gray-800 mb-3">🧱 Pieces for this step:</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {step.bricks_in_step.map((brick, idx) => (
                <div key={idx} className="bg-gradient-to-br from-red-100 to-red-50 border-2 border-red-300 rounded-lg p-3">
                  <p className="font-bold text-red-700">{brick.lego_type}</p>
                  <p className="text-sm text-gray-600">Part ID: {brick.part_id}</p>
                  <p className="text-lg font-bold text-red-600 mt-1">Qty: {brick.quantity}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Layer Summary */}
          {manual.layer_summary[step.layer_z] && (
            <div className="mt-4 p-3 bg-blue-50 rounded border border-blue-300">
              <p className="text-sm font-semibold text-blue-900">💡 Layer Tip:</p>
              <p className="text-sm text-blue-800 mt-1">{manual.layer_summary[step.layer_z]}</p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Controls */}
      <div className="flex gap-3 justify-between items-center">
        <button
          onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
          disabled={currentStep === 0}
          className="bg-gray-400 hover:bg-gray-500 disabled:bg-gray-300 text-white font-bold py-2 px-6 rounded"
        >
          ← Previous
        </button>

        <div className="text-center">
          <div className="relative w-64 h-2 bg-gray-300 rounded-full">
            <div
              className="absolute h-2 bg-blue-500 rounded-full transition-all"
              style={{
                width: `${((currentStep + 1) / manual.total_steps) * 100}%`,
              }}
            />
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Step {currentStep + 1} of {manual.total_steps}
          </p>
        </div>

        <button
          onClick={() => setCurrentStep(Math.min(manual.total_steps - 1, currentStep + 1))}
          disabled={currentStep === manual.total_steps - 1}
          className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white font-bold py-2 px-6 rounded"
        >
          Next →
        </button>
      </div>

      {/* Print Button */}
      <div className="mt-6 text-center">
        <button
          onClick={() => window.print()}
          className="bg-green-500 hover:bg-green-600 text-white font-bold py-3 px-8 rounded-lg text-lg"
        >
          🖨️ Print Instructions
        </button>
      </div>
    </div>
  );
}
