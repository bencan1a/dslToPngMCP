# DSL Reference

Complete reference guide for the Domain Specific Language (DSL) used to define UI mockups for PNG generation.

## Table of Contents

- [Overview](#overview)
- [Document Structure](#document-structure)
- [Element Types](#element-types)
- [Layout System](#layout-system)
- [Style Properties](#style-properties)
- [Responsive Design](#responsive-design)
- [CSS Integration](#css-integration)
- [Examples](#examples)
- [Best Practices](#best-practices)

---

## Overview

The DSL to PNG system uses a JSON or YAML-based Domain Specific Language to define user interface mockups. The DSL provides a structured way to describe UI elements, their layout, styling, and interactions.

### Key Features

- **Multiple Formats**: JSON and YAML support
- **Rich Element Types**: 11+ built-in UI components
- **Flexible Layouts**: Absolute, flexbox, and grid positioning
- **CSS Integration**: Custom CSS and inline styles
- **Responsive Design**: Breakpoint-based responsive layouts
- **Type Safety**: Comprehensive validation and error reporting

### Schema Version

Current DSL schema version: **1.0**

---

## Document Structure

### Basic Document

```json
{
  "title": "Document Title",
  "description": "Document description",
  "width": 800,
  "height": 600,
  "elements": [
    // Array of UI elements
  ],
  "css": "/* Custom CSS styles */",
  "theme": "theme-name",
  "metadata": {},
  "version": "1.0",
  "responsiveBreakpoints": {
    "sm": 640,
    "md": 768, 
    "lg": 1024,
    "xl": 1280
  }
}
```

### Document Properties

| Property | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `title` | string | No | null | Document title for reference |
| `description` | string | No | null | Document description |
| `width` | integer | Yes | 800 | Canvas width in pixels (100-4000) |
| `height` | integer | Yes | 600 | Canvas height in pixels (100-4000) |
| `elements` | array | Yes | [] | Array of UI elements |
| `css` | string | No | "" | Custom CSS styles |
| `theme` | string | No | null | Theme identifier |
| `metadata` | object | No | {} | Additional metadata |
| `version` | string | No | "1.0" | DSL schema version |
| `responsiveBreakpoints` | object | No | default | Responsive breakpoints |

---

## Element Types

### Common Element Properties

All elements share these base properties:

```json
{
  "id": "unique-identifier",
  "type": "element-type",
  "layout": {
    "x": 0,
    "y": 0,
    "width": 100,
    "height": 50
  },
  "style": {
    "background": "#ffffff",
    "color": "#000000"
  },
  "className": "css-class-name",
  "customAttributes": {
    "data-testid": "test-id",
    "aria-label": "Accessibility label"
  },
  "responsive": {
    "sm": { /* Small screen overrides */ },
    "md": { /* Medium screen overrides */ }
  }
}
```

### 1. Button

Interactive button element for actions and navigation.

```json
{
  "type": "button",
  "label": "Click Me",
  "onClick": "handleClick()",
  "onHover": "showTooltip()",
  "layout": {
    "x": 100,
    "y": 50,
    "width": 120,
    "height": 40
  },
  "style": {
    "background": "#007bff",
    "color": "white",
    "fontSize": 16,
    "fontWeight": "bold",
    "borderRadius": "8px",
    "border": "none",
    "cursor": "pointer"
  }
}
```

**Button Properties:**
- `label` (string, required): Button text
- `onClick` (string): Click event handler
- `onHover` (string): Hover event handler

### 2. Text

Display text content with rich formatting options.

```json
{
  "type": "text",
  "text": "Hello World",
  "layout": {
    "x": 10,
    "y": 10,
    "width": 200,
    "height": 30
  },
  "style": {
    "fontSize": 18,
    "fontWeight": "600",
    "color": "#333333",
    "textAlign": "center",
    "lineHeight": 1.5
  }
}
```

**Text Properties:**
- `text` (string, required): Text content
- Supports HTML entities and basic markdown

### 3. Input

Form input elements for data collection.

```json
{
  "type": "input",
  "placeholder": "Enter username",
  "onChange": "validateInput()",
  "layout": {
    "x": 20,
    "y": 100,
    "width": 250,
    "height": 40
  },
  "style": {
    "fontSize": 14,
    "padding": "8px 12px",
    "border": "2px solid #ced4da",
    "borderRadius": "6px",
    "outline": "none"
  },
  "customAttributes": {
    "type": "text",
    "autocomplete": "username",
    "required": "true"
  }
}
```

**Input Properties:**
- `placeholder` (string): Placeholder text
- `onChange` (string): Change event handler
- Use `customAttributes` for input type, validation, etc.

### 4. Image

Display images with various sizing and positioning options.

```json
{
  "type": "image",
  "src": "https://example.com/image.jpg",
  "alt": "Example image",
  "layout": {
    "x": 50,
    "y": 50,
    "width": 200,
    "height": 150
  },
  "style": {
    "objectFit": "cover",
    "borderRadius": "12px",
    "border": "1px solid #e0e0e0"
  }
}
```

**Image Properties:**
- `src` (string, required): Image URL or base64 data
- `alt` (string): Alternative text for accessibility

### 5. Container

Generic container for grouping and organizing child elements.

```json
{
  "type": "container",
  "layout": {
    "x": 0,
    "y": 0,
    "width": 400,
    "height": 300
  },
  "style": {
    "background": "#f8f9fa",
    "border": "1px solid #dee2e6",
    "borderRadius": "8px",
    "padding": "20px"
  },
  "children": [
    {
      "type": "text",
      "text": "Container Content",
      "layout": {"x": 0, "y": 0, "width": 360, "height": 30}
    }
  ]
}
```

**Container Properties:**
- `children` (array): Child elements (positioned relative to container)

### 6. Grid

CSS Grid layout container for complex layouts.

```json
{
  "type": "grid",
  "layout": {
    "x": 0,
    "y": 0,
    "width": 600,
    "height": 400
  },
  "style": {
    "display": "grid",
    "gridTemplateColumns": "repeat(3, 1fr)",
    "gridTemplateRows": "auto auto",
    "gap": "16px",
    "padding": "20px"
  },
  "children": [
    {
      "type": "card",
      "layout": {"width": 180, "height": 120}
    },
    {
      "type": "card", 
      "layout": {"width": 180, "height": 120}
    }
  ]
}
```

**Grid Properties:**
- Uses CSS Grid properties in `style`
- Children automatically placed in grid cells
- Support for `gridTemplateColumns`, `gridTemplateRows`, `gap`, etc.

### 7. Flex

Flexbox layout container for responsive layouts.

```json
{
  "type": "flex",
  "layout": {
    "x": 0,
    "y": 0,
    "width": 500,
    "height": 100
  },
  "style": {
    "display": "flex",
    "flexDirection": "row",
    "justifyContent": "space-between",
    "alignItems": "center",
    "gap": "12px",
    "padding": "16px"
  },
  "children": [
    {
      "type": "button",
      "label": "Button 1",
      "style": {"flex": "1"}
    },
    {
      "type": "button",
      "label": "Button 2", 
      "style": {"flex": "1"}
    }
  ]
}
```

**Flex Properties:**
- Uses CSS Flexbox properties in `style`
- Supports `flexDirection`, `justifyContent`, `alignItems`, `gap`, etc.
- Children can use `flex`, `flexGrow`, `flexShrink` properties

### 8. Card

Pre-styled container with card-like appearance.

```json
{
  "type": "card",
  "layout": {
    "x": 20,
    "y": 20,
    "width": 300,
    "height": 200
  },
  "style": {
    "background": "white",
    "borderRadius": "12px",
    "padding": "24px",
    "border": "1px solid #e5e7eb",
    "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)"
  },
  "children": [
    {
      "type": "text",
      "text": "Card Title",
      "style": {"fontSize": 18, "fontWeight": "bold"}
    }
  ]
}
```

### 9. Modal

Modal dialog overlay element.

```json
{
  "type": "modal",
  "layout": {
    "x": 100,
    "y": 100,
    "width": 400,
    "height": 300
  },
  "style": {
    "background": "white",
    "borderRadius": "8px",
    "padding": "24px",
    "boxShadow": "0 25px 50px rgba(0, 0, 0, 0.25)",
    "position": "relative",
    "zIndex": 1000
  },
  "children": [
    {
      "type": "text",
      "text": "Modal Content",
      "layout": {"x": 0, "y": 0, "width": 352, "height": 30}
    }
  ]
}
```

### 10. Navbar

Navigation bar component.

```json
{
  "type": "navbar",
  "layout": {
    "x": 0,
    "y": 0,
    "width": 800,
    "height": 60
  },
  "style": {
    "background": "#1f2937",
    "color": "white",
    "padding": "0 24px",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "space-between"
  },
  "children": [
    {
      "type": "text",
      "text": "Brand Name",
      "style": {"fontSize": 20, "fontWeight": "bold"}
    }
  ]
}
```

### 11. Sidebar

Sidebar navigation component.

```json
{
  "type": "sidebar",
  "layout": {
    "x": 0,
    "y": 0,
    "width": 250,
    "height": 600
  },
  "style": {
    "background": "#f8f9fa",
    "borderRight": "1px solid #dee2e6",
    "padding": "20px"
  },
  "children": [
    {
      "type": "text",
      "text": "Navigation",
      "style": {"fontSize": 16, "fontWeight": "600", "marginBottom": "16px"}
    }
  ]
}
```

---

## Layout System

### Coordinate System

- Origin (0,0) is at the top-left corner
- X-axis increases to the right
- Y-axis increases downward
- All units are in pixels

### Layout Properties

```json
{
  "layout": {
    "x": 100,           // X position (pixels)
    "y": 50,            // Y position (pixels)
    "width": 200,       // Width (pixels)
    "height": 150,      // Height (pixels)
    "minWidth": 100,    // Minimum width
    "maxWidth": 300,    // Maximum width
    "minHeight": 75,    // Minimum height
    "maxHeight": 200    // Maximum height
  }
}
```

### Positioning Modes

#### 1. Absolute Positioning
Default positioning mode using x, y coordinates.

```json
{
  "layout": {
    "x": 100,
    "y": 50,
    "width": 200,
    "height": 100
  }
}
```

#### 2. Flexbox Positioning
For flex containers, children are positioned by flexbox rules.

```json
{
  "type": "flex",
  "style": {
    "display": "flex",
    "flexDirection": "column",
    "gap": "16px"
  },
  "children": [
    {
      "type": "text",
      "text": "Item 1"
      // No x, y needed - positioned by flex
    }
  ]
}
```

#### 3. Grid Positioning
For grid containers, children are positioned in grid cells.

```json
{
  "type": "grid",
  "style": {
    "display": "grid",
    "gridTemplateColumns": "1fr 1fr",
    "gap": "16px"
  },
  "children": [
    {
      "type": "card",
      "style": {
        "gridColumn": "1",
        "gridRow": "1"
      }
    }
  ]
}
```

### Layout Constraints

- Elements cannot have negative coordinates
- Elements cannot exceed canvas boundaries
- Width and height must be positive
- Container children are positioned relative to container origin

---

## Style Properties

### Typography

```json
{
  "style": {
    "fontSize": 16,                    // Number (px) or string ("16px", "1.2em")
    "fontWeight": "bold",             // "normal", "bold", "600", 400-900
    "fontFamily": "Arial, sans-serif", // Font family string
    "color": "#333333",               // Color (hex, rgb, named)
    "textAlign": "center",            // "left", "center", "right", "justify"
    "lineHeight": 1.5,                // Line height multiplier or px
    "textDecoration": "none",         // "none", "underline", "line-through"
    "textTransform": "uppercase"      // "none", "uppercase", "lowercase", "capitalize"
  }
}
```

### Background and Colors

```json
{
  "style": {
    "background": "#ffffff",                              // Solid color
    "background": "linear-gradient(45deg, #ff0000, #0000ff)", // Gradient
    "background": "url(image.jpg)",                      // Image
    "color": "#000000",                                  // Text color
    "opacity": 0.8                                       // Transparency (0-1)
  }
}
```

### Borders and Spacing

```json
{
  "style": {
    "border": "1px solid #ccc",       // Border shorthand
    "borderRadius": "8px",            // Corner radius
    "padding": "16px",                // Inner spacing
    "margin": "8px",                  // Outer spacing
    "boxShadow": "0 2px 4px rgba(0,0,0,0.1)" // Drop shadow
  }
}
```

### Layout and Positioning

```json
{
  "style": {
    "display": "flex",                // Display type
    "position": "relative",           // Position type
    "zIndex": 10,                     // Stacking order
    "overflow": "hidden",             // Overflow handling
    "cursor": "pointer"               // Cursor style
  }
}
```

### Flexbox Properties

```json
{
  "style": {
    "flexDirection": "row",           // "row", "column", "row-reverse", "column-reverse"
    "justifyContent": "center",       // "flex-start", "center", "space-between", etc.
    "alignItems": "center",           // "flex-start", "center", "stretch", etc.
    "flex": "1",                      // Flex grow/shrink/basis
    "flexWrap": "wrap",               // "nowrap", "wrap", "wrap-reverse"
    "gap": "16px"                     // Space between flex items
  }
}
```

### Grid Properties

```json
{
  "style": {
    "gridTemplateColumns": "repeat(3, 1fr)",  // Column definition
    "gridTemplateRows": "auto auto",          // Row definition
    "gridColumn": "1 / 3",                    // Column span
    "gridRow": "1",                           // Row placement
    "gap": "16px",                            // Grid gap
    "justifyItems": "center",                 // Item alignment
    "alignItems": "center"                    // Item alignment
  }
}
```

### Animations and Transitions

```json
{
  "style": {
    "transition": "all 0.3s ease",           // Transition properties
    "transform": "scale(1.05)",              // Transform functions
    "animation": "fadeIn 1s ease-in-out"     // Animation properties
  }
}
```

---

## Responsive Design

### Breakpoint System

Default responsive breakpoints:

```json
{
  "responsiveBreakpoints": {
    "sm": 640,    // Small devices (≥640px)
    "md": 768,    // Medium devices (≥768px)
    "lg": 1024,   // Large devices (≥1024px)
    "xl": 1280    // Extra large devices (≥1280px)
  }
}
```

### Element-Level Responsive Properties

```json
{
  "type": "text",
  "text": "Responsive Text",
  "layout": {
    "x": 20,
    "y": 20,
    "width": 300,
    "height": 60
  },
  "style": {
    "fontSize": 24,
    "color": "#333"
  },
  "responsive": {
    "sm": {
      "layout": {
        "width": 250,
        "height": 50
      },
      "style": {
        "fontSize": 18
      }
    },
    "md": {
      "style": {
        "fontSize": 20
      }
    },
    "lg": {
      "layout": {
        "width": 400
      },
      "style": {
        "fontSize": 26
      }
    }
  }
}
```

### Responsive Layout Patterns

#### Mobile-First Design

```json
{
  "width": 375,  // Mobile width
  "height": 667,
  "elements": [
    {
      "type": "flex",
      "style": {
        "flexDirection": "column",
        "gap": "16px"
      },
      "responsive": {
        "md": {
          "style": {
            "flexDirection": "row",
            "gap": "24px"
          }
        }
      }
    }
  ]
}
```

#### Desktop-First Design

```json
{
  "width": 1200,  // Desktop width
  "height": 800,
  "elements": [
    {
      "type": "grid",
      "style": {
        "gridTemplateColumns": "repeat(4, 1fr)"
      },
      "responsive": {
        "lg": {
          "style": {
            "gridTemplateColumns": "repeat(3, 1fr)"
          }
        },
        "md": {
          "style": {
            "gridTemplateColumns": "repeat(2, 1fr)"
          }
        },
        "sm": {
          "style": {
            "gridTemplateColumns": "1fr"
          }
        }
      }
    }
  ]
}
```

---

## CSS Integration

### Global CSS

Add global styles to the document:

```json
{
  "css": "body { font-family: 'Inter', sans-serif; background: #f0f0f0; } .custom-button { transition: all 0.3s ease; }"
}
```

### Element-Specific Classes

```json
{
  "type": "button",
  "label": "Styled Button",
  "className": "custom-button primary-btn",
  "style": {
    "background": "#007bff"
  }
}
```

### CSS Custom Properties (Variables)

```json
{
  "css": ":root { --primary-color: #007bff; --border-radius: 8px; }",
  "elements": [
    {
      "type": "button",
      "style": {
        "background": "var(--primary-color)",
        "borderRadius": "var(--border-radius)"
      }
    }
  ]
}
```

### Pseudo-Classes and States

```json
{
  "css": ".dsl-button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); } .dsl-input:focus { border-color: #007bff; box-shadow: 0 0 0 3px rgba(0,123,255,0.25); }"
}
```

### Media Queries

```json
{
  "css": "@media (max-width: 768px) { .dsl-container { padding: 16px; } .dsl-text { fontSize: 14px; } }"
}
```

---

## Examples

### Complete Login Form

```json
{
  "title": "Login Form Example",
  "width": 400,
  "height": 350,
  "elements": [
    {
      "type": "container",
      "id": "login-form",
      "layout": {
        "x": 50,
        "y": 50,
        "width": 300,
        "height": 250
      },
      "style": {
        "background": "white",
        "borderRadius": "12px",
        "padding": "24px",
        "boxShadow": "0 4px 20px rgba(0, 0, 0, 0.1)"
      },
      "children": [
        {
          "type": "text",
          "text": "Welcome Back",
          "layout": {
            "x": 0,
            "y": 0,
            "width": 252,
            "height": 30
          },
          "style": {
            "fontSize": 20,
            "fontWeight": "bold",
            "textAlign": "center",
            "color": "#333"
          }
        },
        {
          "type": "input",
          "placeholder": "Username",
          "layout": {
            "x": 0,
            "y": 50,
            "width": 252,
            "height": 40
          },
          "style": {
            "fontSize": 14,
            "padding": "10px",
            "border": "2px solid #e1e5e9",
            "borderRadius": "6px"
          }
        },
        {
          "type": "input",
          "placeholder": "Password",
          "layout": {
            "x": 0,
            "y": 105,
            "width": 252,
            "height": 40
          },
          "style": {
            "fontSize": 14,
            "padding": "10px",
            "border": "2px solid #e1e5e9",
            "borderRadius": "6px"
          },
          "customAttributes": {
            "type": "password"
          }
        },
        {
          "type": "button",
          "label": "Sign In",
          "layout": {
            "x": 0,
            "y": 160,
            "width": 252,
            "height": 45
          },
          "style": {
            "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            "color": "white",
            "fontSize": 16,
            "fontWeight": "600",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "pointer"
          }
        }
      ]
    }
  ],
  "css": ".dsl-input:focus { border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); } .dsl-button:hover { transform: translateY(-1px); }"
}
```

### Dashboard Grid Layout

```json
{
  "title": "Dashboard Layout",
  "width": 1200,
  "height": 800,
  "elements": [
    {
      "type": "navbar",
      "layout": {
        "x": 0,
        "y": 0,
        "width": 1200,
        "height": 60
      },
      "style": {
        "background": "#1f2937",
        "color": "white",
        "display": "flex",
        "alignItems": "center",
        "padding": "0 24px"
      },
      "children": [
        {
          "type": "text",
          "text": "Analytics Dashboard",
          "style": {
            "fontSize": 18,
            "fontWeight": "bold"
          }
        }
      ]
    },
    {
      "type": "grid",
      "layout": {
        "x": 24,
        "y": 84,
        "width": 1152,
        "height": 200
      },
      "style": {
        "display": "grid",
        "gridTemplateColumns": "repeat(4, 1fr)",
        "gap": "24px"
      },
      "children": [
        {
          "type": "card",
          "style": {
            "background": "white",
            "borderRadius": "8px",
            "padding": "20px",
            "border": "1px solid #e5e7eb"
          },
          "children": [
            {
              "type": "text",
              "text": "Revenue",
              "layout": {
                "x": 0,
                "y": 0,
                "width": 228,
                "height": 20
              },
              "style": {
                "fontSize": 14,
                "color": "#6b7280"
              }
            },
            {
              "type": "text",
              "text": "$47,281",
              "layout": {
                "x": 0,
                "y": 30,
                "width": 228,
                "height": 40
              },
              "style": {
                "fontSize": 28,
                "fontWeight": "bold",
                "color": "#111827"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### Mobile App Interface

```yaml
title: "Mobile App Interface"
width: 375
height: 667
elements:
  - type: "navbar"
    layout:
      x: 0
      y: 0
      width: 375
      height: 60
    style:
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
      color: "white"
      display: "flex"
      alignItems: "center"
      justifyContent: "space-between"
      padding: "0 16px"
    children:
      - type: "text"
        text: "MyApp"
        style:
          fontSize: 18
          fontWeight: "600"

  - type: "flex"
    layout:
      x: 16
      y: 80
      width: 343
      height: 500
    style:
      display: "flex"
      flexDirection: "column"
      gap: "16px"
    children:
      - type: "card"
        style:
          background: "white"
          borderRadius: "16px"
          padding: "20px"
          boxShadow: "0 2px 12px rgba(0,0,0,0.08)"
        children:
          - type: "text"
            text: "Welcome to MyApp"
            layout:
              x: 0
              y: 0
              width: 303
              height: 30
            style:
              fontSize: 18
              fontWeight: "600"
              color: "#1a1a1a"

css: |
  body { 
    background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
```

---

## Best Practices

### Document Organization

1. **Use meaningful IDs**: Assign unique, descriptive IDs to elements
2. **Group related elements**: Use containers to organize related UI components
3. **Consistent naming**: Use consistent naming conventions for classes and IDs
4. **Comment complex layouts**: Add descriptions for complex element structures

### Performance Optimization

1. **Limit element count**: Keep total elements under 100 for optimal performance
2. **Optimize images**: Use appropriately sized images and consider compression
3. **Efficient layouts**: Prefer flexbox/grid over absolute positioning for many elements
4. **Minimize CSS**: Avoid overly complex CSS selectors and properties

### Accessibility

1. **Use semantic structure**: Organize elements in logical hierarchy
2. **Provide alt text**: Include alt attributes for images
3. **Color contrast**: Ensure sufficient color contrast ratios
4. **Focus states**: Define clear focus states for interactive elements

### Responsive Design

1. **Mobile-first approach**: Design for mobile and enhance for larger screens
2. **Touch-friendly sizes**: Use minimum 44px touch targets for mobile
3. **Flexible layouts**: Use relative units and flexible layouts
4. **Test breakpoints**: Verify design works at all defined breakpoints

### Code Quality

1. **Validate DSL**: Always validate DSL before rendering
2. **Use consistent units**: Stick to pixels for consistency
3. **Avoid inline styles when possible**: Use CSS classes for reusable styles
4. **Document custom properties**: Comment complex style combinations

### Error Prevention

1. **Check element bounds**: Ensure elements fit within canvas
2. **Validate hierarchy**: Only nest elements in appropriate containers
3. **Test with real content**: Use realistic content lengths and sizes
4. **Handle edge cases**: Consider empty states and error conditions

---

## Validation Rules

### Document Validation

- Canvas dimensions must be between 100-4000 pixels
- Elements array cannot be empty
- All referenced custom classes must be defined in CSS

### Element Validation

- Element type must be from supported list
- Layout coordinates must be non-negative
- Element must fit within parent container bounds
- Children only allowed on container-type elements

### Style Validation

- Color values must be valid CSS colors
- Numeric values must be positive where applicable
- CSS properties must be valid CSS syntax
- Font families should include fallbacks

For complete validation details, use the validation endpoint:

```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d @your-dsl.json
```

---

## Additional Resources

- [API Documentation](./API.md) - Complete API reference
- [User Guide](./USER_GUIDE.md) - Step-by-step tutorials
- [Examples](./examples/) - Complete example projects
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues and solutions