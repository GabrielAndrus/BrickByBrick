'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import InstructionBook from './InstructionBook';

/**
 * MainLayout Component
 * 
 * Accurately recreates the screenshot design with:
 * - Environment section (left): Red button, 5 red indicators, dashed box
 * - Objects section (right): Teal button, 3 teal indicators, empty space
 * - Framer Motion animations for interactions and state changes
 * - Light gray background matching screenshot
 * - Instruction Book for viewing build steps
 */

interface SectionButtonProps {
  label: string;
  color: 'red' | 'teal';
  indicators: number;
  isActive: boolean;
  onClick: () => void;
}

function SectionButton({ label, color, indicators, isActive, onClick }: SectionButtonProps) {
  const bgColor = color === 'red' ? 'bg-red-600' : 'bg-teal-500';
  const indicatorColor = color === 'red' ? 'bg-red-600' : 'bg-teal-500';
  
  return (
    <div className="flex items-center gap-2 mb-4">
      {/* Main Button */}
      <motion.button
        onClick={onClick}
        className={`${bgColor} text-white px-6 py-2 rounded-full font-medium shadow-sm`}
        whileHover={{ scale: 1.05, boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' }}
        whileTap={{ scale: 0.95 }}
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4 }}
        aria-label={`${label} section button`}
      >
        {label}
      </motion.button>
      
      {/* Indicator Dots */}
      <div className="flex gap-2">
        {Array.from({ length: indicators }).map((_, i) => (
          <motion.button
            key={i}
            onClick={onClick}
            className={`w-3 h-3 ${indicatorColor} rounded-full ${
              isActive ? 'opacity-100' : 'opacity-70'
            }`}
            aria-label={`${label} indicator ${i + 1}`}
            whileHover={{ scale: 1.2 }}
            whileTap={{ scale: 0.9 }}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ 
              opacity: isActive ? 1 : 0.7,
              scale: 1
            }}
            transition={{ 
              delay: i * 0.1,
              duration: 0.3
            }}
          />
        ))}
      </div>
    </div>
  );
}

// Demo data for instruction book (replace with real API data)
const demoManualData = {
  total_steps: 5,
  difficulty: "Easy",
  estimated_time_minutes: 15,
  baseplate: {
    size_studs: [16, 16],
    lego_type: "Baseplate 16x16"
  },
  steps: [
    {
      step_number: 1,
      layer_z: 0,
      bricks_in_step: [
        { part_id: "3001", position: { studs: [0, 0, 0] }, rotation: 0 },
        { part_id: "3001", position: { studs: [4, 0, 0] }, rotation: 0 },
        { part_id: "3003", position: { studs: [8, 0, 0] }, rotation: 0 },
      ],
      piece_counts: { "3001": 2, "3003": 1 },
      instructions: "Start by placing the base layer bricks"
    },
    {
      step_number: 2,
      layer_z: 1,
      bricks_in_step: [
        { part_id: "3001", position: { studs: [0, 0, 1] }, rotation: 0 },
        { part_id: "3004", position: { studs: [4, 0, 1] }, rotation: 90 },
      ],
      piece_counts: { "3001": 1, "3004": 1 },
      instructions: "Build the second layer"
    },
    {
      step_number: 3,
      layer_z: 2,
      bricks_in_step: [
        { part_id: "3003", position: { studs: [0, 0, 2] }, rotation: 0 },
        { part_id: "3003", position: { studs: [2, 0, 2] }, rotation: 0 },
      ],
      piece_counts: { "3003": 2 },
      instructions: "Add support bricks"
    },
    {
      step_number: 4,
      layer_z: 3,
      bricks_in_step: [
        { part_id: "3001", position: { studs: [0, 0, 3] }, rotation: 0 },
      ],
      piece_counts: { "3001": 1 },
      instructions: "Continue building upward"
    },
    {
      step_number: 5,
      layer_z: 4,
      bricks_in_step: [
        { part_id: "3068", position: { studs: [0, 0, 4] }, rotation: 0 },
      ],
      piece_counts: { "3068": 1 },
      instructions: "Place the finishing tile on top"
    }
  ],
  layer_summary: {
    0: "Foundation layer - stable base",
    1: "First wall layer",
    2: "Support structure",
    3: "Upper walls",
    4: "Roof/top finish"
  }
};

const demoPieceCount = {
  total_pieces: 12,
  total_unique: 4,
  breakdown: [
    { part_id: "3001", color_id: 5, quantity: 4, piece_name: "Brick 2x4" },
    { part_id: "3003", color_id: 1, quantity: 3, piece_name: "Brick 2x2" },
    { part_id: "3004", color_id: 15, quantity: 1, piece_name: "Brick 1x2" },
    { part_id: "3068", color_id: 7, quantity: 1, piece_name: "Tile 2x2" },
  ]
};

export default function MainLayout() {
  const [environmentActive, setEnvironmentActive] = useState(true);
  const [objectsActive, setObjectsActive] = useState(false);
  const [showInstructionBook, setShowInstructionBook] = useState(false);

  return (
    <motion.div 
      className="min-h-screen bg-gray-100 p-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      <div className="grid grid-cols-2 gap-6 h-[calc(100vh-8rem)]">
        {/* Left: Environment Section */}
        <motion.div 
          className="flex flex-col"
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <SectionButton
            label="Environment"
            color="red"
            indicators={5}
            isActive={environmentActive}
            onClick={() => setEnvironmentActive(!environmentActive)}
          />
          
          {/* Dashed Box Container */}
          <AnimatePresence mode="wait">
            {environmentActive && (
              <motion.div 
                className="flex-1 border-2 border-dashed border-gray-400 rounded-lg p-8 flex items-center justify-center bg-white/50"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3 }}
              >
                <motion.p 
                  className="text-gray-700 text-lg"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                >
                  whatever tailwind upload
                </motion.p>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Right: Objects Section */}
        <motion.div 
          className="flex flex-col"
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
        >
          <SectionButton
            label="Objects"
            color="teal"
            indicators={3}
            isActive={objectsActive}
            onClick={() => setObjectsActive(!objectsActive)}
          />
          
          {/* Empty Space */}
          <AnimatePresence mode="wait">
            {objectsActive ? (
              <motion.div 
                className="flex-1 bg-transparent"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              />
            ) : (
              <motion.div 
                className="flex-1 bg-transparent"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
              />
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* Instruction Book Button - Fixed position */}
      <motion.button
        onClick={() => setShowInstructionBook(true)}
        className="fixed bottom-6 right-6 bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-full font-semibold shadow-lg flex items-center gap-2 z-40"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
      >
        <span className="text-xl">📖</span>
        <span>Build Instructions</span>
        <span className="bg-white/20 px-2 py-0.5 rounded text-sm ml-1">
          {demoPieceCount.total_pieces} pcs
        </span>
      </motion.button>

      {/* Instruction Book Modal */}
      <AnimatePresence>
        {showInstructionBook && (
          <InstructionBook
            projectName="My LEGO Build"
            manual={demoManualData}
            pieceCount={demoPieceCount}
            isOpen={showInstructionBook}
            onClose={() => setShowInstructionBook(false)}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}
