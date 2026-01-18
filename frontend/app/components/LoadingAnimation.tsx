'use client';

import React from 'react';
import Lottie from 'lottie-react';
// Make sure to place your lottie file in the same folder or update the path
import legoAnimationData from './lego-animation.json'; 

const LoadingAnimation = () => {
  return (
    <div className="flex flex-col items-center justify-center">
      {/* Container for the Lottie animation. 
          The size is kept at 300px to match the scale of the box logo.
      */}
      <div className="w-64 h-64 md:w-80 md:h-80">
        <Lottie 
          animationData={legoAnimationData} 
          loop={true}
          style={{ width: '100%', height: '100%' }}
        />
      </div>

      {/* Optional: LEGO-colored dots below the animation 
          to reinforce your specific color set 
      */}
      <div className="flex gap-2 mt-2">
        <div className="w-2 h-2 rounded-full bg-green-500 animate-bounce" style={{ animationDelay: '0ms' }} />
        <div className="w-2 h-2 rounded-full bg-yellow-400 animate-bounce" style={{ animationDelay: '150ms' }} />
        <div className="w-2 h-2 rounded-full bg-red-600 animate-bounce" style={{ animationDelay: '300ms' }} />
        <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '450ms' }} />
        <div className="w-2 h-2 rounded-full bg-orange-500 animate-bounce" style={{ animationDelay: '600ms' }} />
      </div>
    </div>
  );
};

export default LoadingAnimation;
