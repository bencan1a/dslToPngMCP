# DSL to PNG Examples

This directory contains example DSL documents for testing the DSL to PNG conversion system. Each example demonstrates different features and capabilities of the DSL parser and rendering engine.

## Examples Overview

### 1. Simple Button (`simple_button.json`)
- **Format**: JSON
- **Description**: A basic button demonstration with hover effects
- **Features**: 
  - Basic element layout
  - CSS styling with colors and border radius
  - Hover animations
- **Size**: 400x200px

### 2. Login Form (`login_form.json`)
- **Format**: JSON
- **Description**: A complete login form with modern styling
- **Features**:
  - Container with children elements
  - Input fields with placeholders
  - Gradient backgrounds
  - Focus states and validation styling
- **Size**: 500x400px

### 3. Analytics Dashboard (`dashboard.json`)
- **Format**: JSON
- **Description**: A comprehensive analytics dashboard layout
- **Features**:
  - Navigation bar
  - Grid layout with metric cards
  - Flex containers
  - Complex nested structures
  - Professional styling with shadows and gradients
- **Size**: 1200x800px

### 4. Mobile App Interface (`mobile_app.yaml`)
- **Format**: YAML
- **Description**: A responsive mobile app interface design
- **Features**:
  - YAML format parsing
  - Mobile-optimized layout (375x667px)
  - Vertical flex layouts
  - Card components with icons
  - Action buttons with gradients
- **Size**: 375x667px (iPhone dimensions)

### 5. Error Example (`error_example.json`)
- **Format**: JSON
- **Description**: Intentionally invalid DSL for testing validation
- **Features**:
  - Invalid element types
  - Invalid numeric values
  - Out-of-range properties
  - Invalid parent-child relationships
- **Purpose**: Testing error handling and validation

## Usage

### Via FastAPI REST API

```bash
# Validate DSL
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d @examples/simple_button.json

# Synchronous rendering
curl -X POST "http://localhost:8000/render" \
  -H "Content-Type: application/json" \
  -d @examples/login_form.json

# Asynchronous rendering
curl -X POST "http://localhost:8000/render/async" \
  -H "Content-Type: application/json" \
  -d @examples/dashboard.json
```

### Via MCP Tools

```javascript
// Using the render_ui_mockup tool
{
  "tool": "render_ui_mockup",
  "arguments": {
    "dsl_content": "...", // Content from any example file
    "width": 800,
    "height": 600,
    "async_mode": false,
    "options": {
      "device_scale_factor": 1.0,
      "wait_for_load": true,
      "optimize_png": true
    }
  }
}

// Using the validate_dsl tool
{
  "tool": "validate_dsl",
  "arguments": {
    "dsl_content": "...", // Content from any example file
    "strict": false
  }
}
```

## DSL Schema Reference

### Supported Element Types
- `button` - Interactive buttons
- `text` - Text content
- `input` - Form input fields
- `image` - Images with src/alt attributes
- `container` - Generic containers for grouping
- `grid` - CSS Grid layouts
- `flex` - CSS Flexbox layouts
- `card` - Styled card components
- `modal` - Modal dialog components
- `navbar` - Navigation bars
- `sidebar` - Sidebar components

### Layout Properties
- `x`, `y` - Position coordinates (pixels)
- `width`, `height` - Dimensions (pixels)
- `minWidth`, `maxWidth` - Responsive width constraints
- `minHeight`, `maxHeight` - Responsive height constraints

### Style Properties
- `background` - Background color or gradient
- `color` - Text color
- `fontSize` - Font size (pixels or CSS units)
- `fontWeight` - Font weight
- `fontFamily` - Font family
- `border` - Border styling
- `borderRadius` - Border radius
- `margin`, `padding` - Spacing
- `opacity` - Transparency (0.0 to 1.0)
- Layout: `display`, `position`, `flexDirection`, `justifyContent`, `alignItems`
- Animation: `transition`, `transform`

### Document Properties
- `title` - Document title
- `description` - Document description
- `width`, `height` - Canvas dimensions
- `elements` - Array of UI elements
- `css` - Custom CSS styles
- `theme` - Theme name
- `metadata` - Additional metadata
- `responsiveBreakpoints` - Responsive design breakpoints

## Performance Considerations

- **Small UIs** (< 500x500px): Use synchronous rendering for immediate results
- **Complex Dashboards** (> 1000px width): Use asynchronous rendering for better performance
- **Mobile Layouts**: Optimize for 375x667px (iPhone) or 360x640px (Android)
- **File Size**: Optimized PNGs typically range from 10KB to 500KB depending on complexity

## Troubleshooting

### Common Validation Errors
1. **Invalid element type**: Check supported element types list
2. **Negative dimensions**: Width and height must be positive
3. **Invalid children**: Only container elements can have children
4. **Out of range opacity**: Must be between 0.0 and 1.0
5. **Missing required fields**: All elements must have a `type` property

### Performance Issues
1. **Large canvases**: Consider splitting into smaller components
2. **Complex nesting**: Limit nesting depth to 5-6 levels
3. **Too many elements**: Consider using grid/flex layouts for efficiency

For more examples and advanced usage, check the test files in the `tests/` directory.