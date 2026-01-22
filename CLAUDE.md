# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a static website for Lerna Babikyan Creative Dance Studio. The site is built with vanilla HTML, CSS, and JavaScript without any build tools or frameworks.

## Development

### Running Locally

Since this is a static site, you can:

1. Open `index.html` directly in a browser
2. Use a local server (recommended to avoid CORS issues):
   ```bash
   python3 -m http.server 8000
   # or
   npx serve .
   ```

### File Structure

- `index.html` - Single-page application with all sections (hero, about, classes, gallery, contact)
- `css/style.css` - All styles with CSS custom properties (variables) and responsive breakpoints
- `js/main.js` - Vanilla JavaScript for interactive features

## Architecture

### CSS Organization

The stylesheet is organized into sections:
- CSS Variables (`:root`) - color palette, spacing, transitions, shadows, border-radius
- Reset and base styles
- Utility classes (`.container`, `.section`, `.btn`)
- Component styles (navigation, hero, about, classes, gallery, contact, footer)
- Animations (`.fade-in`)
- Responsive breakpoints (@media queries for 1024px, 768px, 480px)

**Color Scheme**: Warm palette with accent color `#FF6B6B` (coral/pink)

### JavaScript Components

All components are initialized on `DOMContentLoaded`:
- `initNavigation()` - Mobile hamburger menu toggle
- `initSmoothScroll()` - Smooth scrolling for anchor links and active link highlighting
- `initNavbarScroll()` - Navbar shadow effect on scroll
- `initScrollAnimations()` - Intersection Observer for fade-in animations
- `initLightbox()` - Gallery image viewer with keyboard navigation

### Responsive Design

Three breakpoints:
- Tablet (1024px): 2-column classes grid
- Mobile (768px): Mobile navigation, single-column layouts
- Small mobile (480px): Reduced spacing and font sizes

## Design Patterns

- **Single-page layout**: All content in index.html with section-based navigation
- **CSS Variables**: All design tokens defined in `:root` for consistency
- **Progressive enhancement**: Core content accessible without JavaScript
- **Intersection Observer**: Used for scroll animations instead of scroll event listeners
- **Placeholder content**: Image placeholders throughout for future real images
