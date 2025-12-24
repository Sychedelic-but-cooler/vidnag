# Vidnag Main Page - Glass Theme Layout

## Visual Wireframe

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Top Bar - Glassmorphic with gradient backdrop]                     │
│                                                                      │
│  Vidnag                                    👤 ⚙️ 🛡️ ❓ 🎨 [Logout] │
│  Welcome back, Username!                                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ [Tab Navigation - Glass bar below header]                           │
│                                                                      │
│  📥 Video Downloads  |  🛠️ Tools  |  📁 Browser  |  📊 Logs        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ [Main Content - Glass cards on gradient background]                 │
│                                                                      │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │ [Glass Card - Active Tab Content]                         │    │
│   │                                                            │    │
│   │  Content varies by active tab                             │    │
│   │                                                            │    │
│   │                                                            │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Layout Structure

### 1. Top Bar (Glassmorphic Header)

**Left Side:**
- **Vidnag** - Brand name/logo (larger text)
- **Welcome back, [Username]!** - Greeting text below logo

**Right Side:**
- 👤 **Profile** - User profile
- ⚙️ **Settings** - App settings
- 🛡️ **Admin** - Admin portal (only if is_admin)
- ❓ **Help** - Link to GitHub
- 🎨 **Theme** - Theme switcher
- **[Logout]** - Logout button

### 2. Tab Navigation (Glass Bar)

Horizontal tabs spanning full width:
- 📥 **Video Downloads**
- 🛠️ **Video Tools**
- 📁 **File Browser**
- 📊 **Logs**

Active tab has brighter glass effect and accent color.

### 3. Main Content Area

Scrollable content with glass cards on animated gradient background.

---

## Glassmorphism Design System

### Visual Effects

**Frosted Glass:**
```css
background: rgba(255, 255, 255, 0.1);
backdrop-filter: blur(10px);
border: 1px solid rgba(255, 255, 255, 0.2);
box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
```

**Gradient Background:**
```css
/* Animated mesh gradient */
background: linear-gradient(45deg,
    var(--color-primary),
    var(--color-secondary),
    var(--color-primary-light)
);
animation: gradientShift 15s ease infinite;
```

**Glass Cards:**
- Semi-transparent with blur
- Subtle border glow
- Smooth hover effects
- Elevated shadows

### Color Adjustments for Glass

**Light Mode Glass:**
- Lighter backgrounds: `rgba(255, 255, 255, 0.7)`
- Darker text for contrast
- Subtle shadows

**Dark Mode Glass:**
- Darker backgrounds: `rgba(0, 0, 0, 0.4)`
- Lighter text
- Stronger glow effects

---

## Technical Specifications

### CSS Architecture

```
frontend/css/
├── variables.css      # (existing) Theme variables
├── glass.css          # NEW: Glassmorphism effects
├── main-layout.css    # NEW: Main page layout
├── header.css         # NEW: Top bar styles
├── tabs.css           # NEW: Tab navigation
└── content.css        # NEW: Main content area
```

### Glass Theme Variables

```css
/* Glass effects */
--glass-bg: rgba(255, 255, 255, 0.1);
--glass-border: rgba(255, 255, 255, 0.2);
--glass-blur: blur(10px);
--glass-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);

/* Gradient layers */
--gradient-1: var(--color-primary);
--gradient-2: var(--color-secondary);
--gradient-3: var(--color-primary-light);
```

### Responsive Design

**Desktop (> 1024px):**
- Full layout with all icons
- Tabs side-by-side
- Multiple columns for content

**Tablet (768px - 1024px):**
- Compact icon labels
- Tabs remain horizontal
- Single column content

**Mobile (< 768px):**
- Icons only (no labels)
- Tabs become horizontal scroll
- Stack content vertically

---

## Animation Effects

### Gradient Animation
```css
@keyframes gradientShift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}
```

### Glass Hover
```css
.glass:hover {
    background: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.3);
    transform: translateY(-2px);
}
```

### Tab Transition
```css
.tab {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.tab.active {
    background: rgba(255, 255, 255, 0.2);
    box-shadow: 0 0 20px rgba(var(--color-primary), 0.5);
}
```

---

## Next Steps

1. ✅ Layout structure defined
2. ⏳ Create glassmorphism CSS system
3. ⏳ Build header component
4. ⏳ Create tab navigation
5. ⏳ Implement main content area
6. ⏳ Get requirements for each tab's content

**Ready to build the glass theme! Tell me what content you want in each tab and I'll create the full implementation.**
