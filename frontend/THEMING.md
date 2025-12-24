# Vidnag Theme System

A robust, easy-to-extend CSS theming system with light/dark modes and multiple color themes.

## Features

✅ Light and Dark modes
✅ 7 color themes (Blue, Green, Purple, Red, Orange, Teal, Pink)
✅ Automatic persistence (localStorage)
✅ System preference detection
✅ Smooth transitions
✅ Easy to add new themes

## Architecture

### 1. CSS Variables (`frontend/css/variables.css`)
All theme colors, spacing, typography, and design tokens are defined as CSS custom properties:

```css
/* Access anywhere in CSS */
color: var(--text-primary);
background: var(--bg-secondary);
padding: var(--space-lg);
border-radius: var(--radius-md);
```

### 2. Theme Manager (`frontend/js/theme.js`)
JavaScript API for theme switching and persistence:

```javascript
// API
ThemeManager.setTheme('dark');      // Switch to dark mode
ThemeManager.setColor('purple');    // Switch to purple
ThemeManager.toggleTheme();         // Toggle light/dark
ThemeManager.getCurrentTheme();     // Get current theme
ThemeManager.getCurrentColor();     // Get current color
ThemeManager.reset();               // Reset to defaults
```

### 3. Theme Switcher Component (`frontend/js/theme-switcher-component.js`)
Floating UI button for easy theme switching.

## Adding a New Color Theme

It's incredibly easy! Just add a new section to `variables.css`:

```css
/* Yellow Theme */
[data-color="yellow"] {
    --color-primary: #eab308;
    --color-primary-hover: #ca8a04;
    --color-primary-light: #fbbf24;
    --color-primary-dark: #a16207;

    --color-secondary: #f59e0b;
    --color-secondary-hover: #d97706;
    --color-secondary-light: #fbbf24;
    --color-secondary-dark: #b45309;
}
```

Then add it to the color options:
1. Update `ThemeManager.COLORS` array in `theme.js`
2. Add a button in `theme-switcher-component.js`
3. Add a color swatch in `theme-switcher.css`

That's it! The theme will automatically work with both light and dark modes.

## Using Theme Variables in New CSS

Always use CSS variables instead of hardcoded colors:

```css
/* ✅ Good - Uses theme variables */
.my-component {
    background: var(--surface);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
    padding: var(--space-md);
    border-radius: var(--radius-lg);
}

/* ❌ Bad - Hardcoded colors */
.my-component {
    background: #ffffff;
    color: #212529;
    border: 1px solid #dee2e6;
    padding: 16px;
    border-radius: 12px;
}
```

## Available Variables

### Colors
- `--color-primary` - Primary brand color
- `--color-secondary` - Secondary brand color
- `--text-primary`, `--text-secondary`, `--text-tertiary` - Text colors
- `--bg-primary`, `--bg-secondary`, `--bg-tertiary` - Background colors
- `--surface` - Card/modal background
- `--border-primary` - Border colors
- `--color-success`, `--color-warning`, `--color-error`, `--color-info` - State colors

### Spacing
- `--space-xs` through `--space-3xl` (4px to 64px)

### Typography
- `--text-xs` through `--text-4xl` (12px to 36px)
- `--font-normal`, `--font-medium`, `--font-semibold`, `--font-bold`

### Other
- `--radius-sm` through `--radius-xl` - Border radius
- `--shadow-sm` through `--shadow-xl` - Box shadows
- `--transition-fast`, `--transition-base`, `--transition-slow` - Transitions

## Events

Listen for theme changes:

```javascript
window.addEventListener('themechange', (e) => {
    console.log('Theme changed:', e.detail.theme, e.detail.color);
});

window.addEventListener('colorchange', (e) => {
    console.log('Color changed:', e.detail.color);
});
```

## Browser Support

Works in all modern browsers that support CSS custom properties:
- Chrome 49+
- Firefox 31+
- Safari 9.1+
- Edge 15+

## Example: Creating a New Page

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Always load variables.css first -->
    <link rel="stylesheet" href="/static/css/variables.css">
    <link rel="stylesheet" href="/static/css/your-page.css">
    <link rel="stylesheet" href="/static/css/theme-switcher.css">

    <!-- Load theme.js early to prevent flash -->
    <script src="/static/js/theme.js"></script>
</head>
<body>
    <!-- Your content -->

    <!-- Load theme switcher at end -->
    <script src="/static/js/theme-switcher-component.js"></script>
</body>
</html>
```

## Tips

1. **Always use variables** - Don't hardcode colors or spacing
2. **Test both modes** - Check your UI in light and dark modes
3. **Smooth transitions** - Use `transition: background var(--transition-base)` for smooth theme changes
4. **Semantic naming** - Use `--text-primary` not `--color-black`
5. **Keep it simple** - Don't override theme colors unnecessarily

## Future Enhancements

- [ ] High contrast mode
- [ ] User-uploaded custom themes
- [ ] Theme preview before applying
- [ ] Sync themes across devices (requires backend)
- [ ] Scheduled theme switching (auto dark mode at night)
