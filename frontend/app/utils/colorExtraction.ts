/**
 * Utility functions for extracting colors from images and determining optimal text colors
 */

// Extract dominant color from an image URL
export const extractDominantColor = async (imageUrl: string): Promise<string> => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        if (!ctx) {
          resolve('#6B7280'); // fallback gray
          return;
        }
        
        // Scale down for performance
        const scaledSize = 50;
        canvas.width = scaledSize;
        canvas.height = scaledSize;
        
        ctx.drawImage(img, 0, 0, scaledSize, scaledSize);
        const imageData = ctx.getImageData(0, 0, scaledSize, scaledSize);
        const pixels = imageData.data;
        
        // Count color frequencies
        const colorCounts: { [key: string]: number } = {};
        
        for (let i = 0; i < pixels.length; i += 4) {
          const r = pixels[i];
          const g = pixels[i + 1];
          const b = pixels[i + 2];
          const alpha = pixels[i + 3];
          
          // Skip transparent pixels
          if (alpha < 128) continue;
          
          // Group similar colors by reducing precision
          const roundedR = Math.round(r / 10) * 10;
          const roundedG = Math.round(g / 10) * 10;
          const roundedB = Math.round(b / 10) * 10;
          
          const colorKey = `${roundedR},${roundedG},${roundedB}`;
          colorCounts[colorKey] = (colorCounts[colorKey] || 0) + 1;
        }
        
        // Find the most frequent color
        let maxCount = 0;
        let dominantColor = '107,114,128'; // fallback gray
        
        for (const [color, count] of Object.entries(colorCounts)) {
          if (count > maxCount) {
            maxCount = count;
            dominantColor = color;
          }
        }
        
        const [r, g, b] = dominantColor.split(',').map(Number);
        
        // Adjust saturation and brightness for better UI appearance
        const adjustedColor = adjustColorForUI(r, g, b);
        resolve(adjustedColor);
        
      } catch (error) {
        console.error('Error extracting color:', error);
        resolve('#6B7280'); // fallback gray
      }
    };
    
    img.onerror = () => {
      resolve('#6B7280'); // fallback gray
    };
    
    img.src = imageUrl;
  });
};

// Adjust color for better UI appearance (soften and ensure good contrast)
const adjustColorForUI = (r: number, g: number, b: number): string => {
  // Convert to HSL for easier manipulation
  const [h, s, l] = rgbToHsl(r, g, b);
  
  // Reduce saturation and adjust lightness for better backgrounds
  const adjustedS = Math.min(s * 0.6, 0.4); // Reduce saturation
  const adjustedL = Math.max(Math.min(l, 0.85), 0.15); // Keep lightness in reasonable range
  
  const [newR, newG, newB] = hslToRgb(h, adjustedS, adjustedL);
  
  return `rgb(${Math.round(newR)}, ${Math.round(newG)}, ${Math.round(newB)})`;
};

// Convert RGB to HSL
const rgbToHsl = (r: number, g: number, b: number): [number, number, number] => {
  r /= 255;
  g /= 255;
  b /= 255;
  
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;
  
  if (max === min) {
    h = s = 0; // achromatic
  } else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }
  
  return [h, s, l];
};

// Convert HSL to RGB
const hslToRgb = (h: number, s: number, l: number): [number, number, number] => {
  let r, g, b;
  
  if (s === 0) {
    r = g = b = l; // achromatic
  } else {
    const hue2rgb = (p: number, q: number, t: number) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };
    
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }
  
  return [r * 255, g * 255, b * 255];
};

// Get luminance of a color
const getLuminance = (r: number, g: number, b: number): number => {
  const [rs, gs, bs] = [r, g, b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
};

// Determine if text should be white or black based on background color
export const getOptimalTextColor = (backgroundColor: string): string => {
  // Parse RGB from string like "rgb(255, 255, 255)"
  const match = backgroundColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (!match) return '#000000'; // fallback to black
  
  const [, r, g, b] = match.map(Number);
  const luminance = getLuminance(r, g, b);
  
  // Use white text on dark backgrounds, black on light backgrounds
  return luminance > 0.5 ? '#000000' : '#FFFFFF';
};

// Create a subtle gradient version of the color for more visual appeal
export const createGradientBackground = (baseColor: string): string => {
  const match = baseColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (!match) return baseColor;
  
  const [, r, g, b] = match.map(Number);
  
  // Create a slightly lighter version for gradient
  const lighterR = Math.min(255, r + 20);
  const lighterG = Math.min(255, g + 20);
  const lighterB = Math.min(255, b + 20);
  
  return `linear-gradient(135deg, ${baseColor} 0%, rgb(${lighterR}, ${lighterG}, ${lighterB}) 100%)`;
}; 