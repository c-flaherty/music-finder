import { useEffect } from 'react';

export const useTouchPreventHorizontalScroll = () => {
  useEffect(() => {
    let startX = 0;
    let startY = 0;
    
    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches && e.touches.length === 1) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
      }
    };
    
    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches && e.touches.length === 1) {
        const dx = Math.abs(e.touches[0].clientX - startX);
        const dy = Math.abs(e.touches[0].clientY - startY);
        if (dx > dy && dx > 0) {
          e.preventDefault();
        }
      }
    };
    
    document.body.addEventListener('touchstart', handleTouchStart, { passive: false });
    document.body.addEventListener('touchmove', handleTouchMove, { passive: false });
    
    return () => {
      document.body.removeEventListener('touchstart', handleTouchStart);
      document.body.removeEventListener('touchmove', handleTouchMove);
    };
  }, []);
}; 