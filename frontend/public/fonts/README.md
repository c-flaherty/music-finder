# Fonts Directory

This directory contains all the web fonts for the music-finder project, now optimized with WOFF2 format for better performance.

## Available Fonts

### Primary Fonts
- **SF Pro** - Main UI font (Variable font with weights 100-900)
- **Proxima Nova** - Secondary font with multiple weights

### Display & Accent Fonts
- **Roobert** - Modern sans-serif (Variable)
- **Rubik** - Rounded sans-serif (Variable)
- **Plus Jakarta Sans** - Clean geometric (Variable)
- **Manrope** - Modern sans-serif (Variable)

### Decorative Fonts
- **Playwrite CU** - Handwriting style (Variable)
- **DynaPuff** - Bubble font (Variable width & weight)
- **Chewy** - Fun display font
- **Cherry Bomb One** - Bold display font
- **Doto** - Rounded display font (Variable)

## Font Formats

All fonts are now available in multiple formats for optimal browser support:

1. **WOFF2** - Modern, highly compressed format (primary)
2. **WOFF** - Older web font format (fallback)
3. **TTF/OTF** - Traditional font formats (final fallback)

### Performance Benefits of WOFF2
- ~30% smaller file sizes compared to WOFF
- Better compression algorithm
- Faster loading times
- Supported by all modern browsers

## Usage

### Import All Fonts
```css
@import url('/fonts/fonts.css');
```

### Use in CSS
```css
/* SF Pro (Primary) */
font-family: 'SF Pro', -apple-system, BlinkMacSystemFont, sans-serif;

/* Proxima Nova */
font-family: 'Proxima Nova', 'SF Pro', sans-serif;

/* Variable Fonts */
font-family: 'Rubik', sans-serif;
font-weight: 300; /* or any value between 300-900 */
```

### Tailwind CSS Classes (if configured)
```html
<div class="font-sf-pro">SF Pro text</div>
<div class="font-rubik font-medium">Rubik medium weight</div>
```

## File Structure

```
fonts/
├── fonts.css                 # Main font definitions
├── SF-Pro/                   # Apple SF Pro family
│   ├── *.woff2               # WOFF2 versions
│   ├── *.ttf                 # TTF versions  
│   └── *.otf                 # OTF versions
├── proximanova/              # Proxima Nova family
│   ├── *-webfont.woff2       # WOFF2 versions
│   ├── *-webfont.woff        # WOFF versions
│   └── *-webfont.ttf         # TTF versions
├── Rubik/                    # Google Rubik family
│   ├── *.woff2               # WOFF2 versions
│   ├── *.ttf                 # TTF versions
│   └── static/               # Individual weight files
└── [other font families]/    # Additional font families
```

## Browser Support

- **WOFF2**: Chrome 36+, Firefox 39+, Safari 12+, Edge 14+
- **WOFF**: All modern browsers
- **TTF/OTF**: Universal fallback

## Performance Tips

1. **Preload critical fonts** in your HTML:
```html
<link rel="preload" href="/fonts/SF-Pro/SF-Pro.woff2" as="font" type="font/woff2" crossorigin>
```

2. **Use font-display: swap** for better loading experience (already configured)

3. **Subset fonts** if you only need specific characters/languages

## Total WOFF2 Files Created

- **43 WOFF2 files** converted from existing TTF/OTF fonts
- **Estimated 30-40% size reduction** compared to original formats
- **Improved loading performance** across the entire application 