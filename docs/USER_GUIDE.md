# User Guide

Complete guide to using the DSL to PNG MCP Server for creating beautiful UI mockups from Domain Specific Language definitions.

## Table of Contents

- [Quick Start](#quick-start)
- [Understanding DSL](#understanding-dsl)
- [Basic Tutorials](#basic-tutorials)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)
- [Performance Optimization](#performance-optimization)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. First DSL Document

Create your first DSL document to render a simple button:

```json
{
  "title": "My First Button",
  "width": 400,
  "height": 200,
  "elements": [
    {
      "type": "button",
      "layout": {
        "x": 150,
        "y": 80,
        "width": 100,
        "height": 40
      },
      "style": {
        "background": "#007bff",
        "color": "white",
        "borderRadius": "8px"
      },
      "label": "Click Me!"
    }
  ]
}
```

### 2. Render Using REST API

```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d @my-first-button.json \
  --output button.png
```

### 3. Validate Before Rendering

Always validate your DSL first:

```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d @my-first-button.json
```

---

## Understanding DSL

### Document Structure

Every DSL document has the following basic structure:

```json
{
  "title": "Document title (optional)",
  "description": "Document description (optional)",
  "width": 800,
  "height": 600,
  "elements": [
    // Array of UI elements
  ],
  "css": "/* Custom CSS styles */",
  "theme": "theme-name (optional)"
}
```

### Core Concepts

#### Canvas
- **Width/Height**: Define the render area in pixels (100-4000px)
- **Background**: Controlled via CSS or transparent

#### Elements
- **Type**: Defines the element kind (button, text, input, etc.)
- **Layout**: Position and size properties
- **Style**: Visual appearance properties
- **Content**: Text, labels, or other content

#### Hierarchy
- **Containers**: Can hold child elements
- **Children**: Nested elements within containers
- **Z-index**: Layering control via CSS

### Supported Formats

#### JSON Format
```json
{
  "width": 400,
  "height": 300,
  "elements": [
    {
      "type": "text",
      "text": "Hello World",
      "layout": {"x": 100, "y": 100, "width": 200, "height": 50}
    }
  ]
}
```

#### YAML Format
```yaml
width: 400
height: 300
elements:
  - type: text
    text: "Hello World"
    layout:
      x: 100
      y: 100
      width: 200
      height: 50
```

---

## Basic Tutorials

### Tutorial 1: Creating a Simple Login Form

Let's build a login form step by step.

#### Step 1: Create the Container

```json
{
  "title": "Login Form Tutorial",
  "width": 400,
  "height": 300,
  "elements": [
    {
      "type": "container",
      "id": "login-container",
      "layout": {
        "x": 50,
        "y": 50,
        "width": 300,
        "height": 200
      },
      "style": {
        "background": "#f8f9fa",
        "borderRadius": "12px",
        "padding": "20px",
        "border": "1px solid #e9ecef"
      },
      "children": []
    }
  ]
}
```

#### Step 2: Add the Title

```json
{
  "children": [
    {
      "type": "text",
      "id": "title",
      "layout": {
        "x": 0,
        "y": 0,
        "width": 260,
        "height": 30
      },
      "style": {
        "fontSize": 20,
        "fontWeight": "bold",
        "color": "#343a40",
        "textAlign": "center"
      },
      "text": "Welcome Back"
    }
  ]
}
```

#### Step 3: Add Input Fields

```json
{
  "children": [
    // Previous title element...
    {
      "type": "input",
      "id": "username",
      "layout": {
        "x": 0,
        "y": 40,
        "width": 260,
        "height": 35
      },
      "style": {
        "fontSize": 14,
        "padding": "8px 12px",
        "borderRadius": "6px",
        "border": "2px solid #ced4da"
      },
      "placeholder": "Username"
    },
    {
      "type": "input",
      "id": "password",
      "layout": {
        "x": 0,
        "y": 85,
        "width": 260,
        "height": 35
      },
      "style": {
        "fontSize": 14,
        "padding": "8px 12px",
        "borderRadius": "6px",
        "border": "2px solid #ced4da"
      },
      "placeholder": "Password"
    }
  ]
}
```

#### Step 4: Add the Submit Button

```json
{
  "children": [
    // Previous elements...
    {
      "type": "button",
      "id": "submit-btn",
      "layout": {
        "x": 0,
        "y": 135,
        "width": 260,
        "height": 40
      },
      "style": {
        "background": "#007bff",
        "color": "white",
        "fontSize": 16,
        "fontWeight": "600",
        "borderRadius": "8px",
        "border": "none"
      },
      "label": "Sign In"
    }
  ]
}
```

#### Complete Login Form

[See `examples/login_form.json`](../examples/login_form.json) for the complete implementation.

### Tutorial 2: Building a Dashboard Layout

#### Step 1: Create Navigation Bar

```json
{
  "type": "navbar",
  "id": "top-nav",
  "layout": {
    "x": 0,
    "y": 0,
    "width": 1200,
    "height": 60
  },
  "style": {
    "background": "#1f2937",
    "color": "white",
    "padding": "0 24px",
    "display": "flex",
    "alignItems": "center"
  },
  "children": [
    {
      "type": "text",
      "text": "Analytics Dashboard",
      "style": {
        "fontSize": 20,
        "fontWeight": "bold",
        "color": "#60a5fa"
      }
    }
  ]
}
```

#### Step 2: Add Metrics Grid

```json
{
  "type": "grid",
  "id": "metrics-grid",
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
    // Metric cards here
  ]
}
```

[See `examples/dashboard.json`](../examples/dashboard.json) for the complete dashboard implementation.

### Tutorial 3: Mobile App Interface

Learn to create mobile-responsive layouts:

#### Key Mobile Design Principles

1. **Smaller Canvas**: Use mobile dimensions (375x667px for iPhone)
2. **Touch-Friendly Elements**: Minimum 44px height for buttons
3. **Readable Text**: Minimum 16px font size
4. **Proper Spacing**: Use adequate margins and padding

[See `examples/mobile_app.yaml`](../examples/mobile_app.yaml) for a complete mobile interface example.

---

## Advanced Features

### Responsive Design

#### Breakpoint Configuration

```json
{
  "responsiveBreakpoints": {
    "sm": 640,
    "md": 768,
    "lg": 1024,
    "xl": 1280
  }
}
```

#### Element-Level Responsive Properties

```json
{
  "type": "text",
  "text": "Responsive Text",
  "layout": {
    "x": 20,
    "y": 20,
    "width": 300,
    "height": 40
  },
  "responsive": {
    "sm": {
      "layout": {"width": 250},
      "style": {"fontSize": 14}
    },
    "md": {
      "layout": {"width": 350},
      "style": {"fontSize": 16}
    }
  }
}
```

### Layout Systems

#### Flexbox Layout

```json
{
  "type": "flex",
  "id": "flex-container",
  "style": {
    "display": "flex",
    "flexDirection": "row",
    "justifyContent": "space-between",
    "alignItems": "center",
    "gap": "16px"
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

#### Grid Layout

```json
{
  "type": "grid",
  "id": "grid-container",
  "style": {
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))",
    "gridTemplateRows": "auto",
    "gap": "20px"
  },
  "children": [
    {"type": "card", "content": "Card 1"},
    {"type": "card", "content": "Card 2"},
    {"type": "card", "content": "Card 3"}
  ]
}
```

### Custom CSS Integration

#### Global Styles

```json
{
  "css": "body { font-family: 'Inter', sans-serif; background: #f0f0f0; }"
}
```

#### Element-Specific Classes

```json
{
  "type": "button",
  "className": "custom-button",
  "css": ".custom-button { transition: all 0.3s ease; } .custom-button:hover { transform: scale(1.05); }"
}
```

### Interactive Elements

#### Event Handlers

```json
{
  "type": "button",
  "label": "Interactive Button",
  "onClick": "handleClick()",
  "onHover": "showTooltip()",
  "onChange": "updateState()"
}
```

#### Custom Attributes

```json
{
  "type": "input",
  "customAttributes": {
    "data-testid": "username-input",
    "aria-label": "Enter your username",
    "autocomplete": "username"
  }
}
```

---

## Best Practices

### Design Guidelines

#### 1. Consistent Spacing

Use a spacing system (8px grid):

```json
{
  "style": {
    "margin": "8px",      // 1 unit
    "padding": "16px",    // 2 units
    "gap": "24px"         // 3 units
  }
}
```

#### 2. Typography Hierarchy

```json
{
  "heading1": {"fontSize": 32, "fontWeight": "bold"},
  "heading2": {"fontSize": 24, "fontWeight": "600"},
  "body": {"fontSize": 16, "fontWeight": "400"},
  "caption": {"fontSize": 14, "fontWeight": "400"}
}
```

#### 3. Color System

```json
{
  "colors": {
    "primary": "#007bff",
    "secondary": "#6c757d", 
    "success": "#28a745",
    "danger": "#dc3545",
    "warning": "#ffc107",
    "info": "#17a2b8"
  }
}
```

### Performance Guidelines

#### 1. Optimize Element Count

- Keep total elements under 100 for fast rendering
- Use containers to group related elements
- Avoid deeply nested structures (max 5 levels)

#### 2. Efficient Layouts

```json
// Good: Use flexbox for simple layouts
{
  "type": "flex",
  "style": {"display": "flex", "gap": "16px"}
}

// Avoid: Complex absolute positioning
{
  "type": "container",
  "children": [
    {"layout": {"x": 10, "y": 20}},
    {"layout": {"x": 30, "y": 45}},
    // Many positioned elements...
  ]
}
```

#### 3. CSS Optimization

```css
/* Good: Use efficient selectors */
.button { background: #007bff; }

/* Avoid: Complex selectors */
.container .row .col .button:nth-child(3) { background: #007bff; }
```

### Accessibility

#### 1. Semantic HTML

```json
{
  "type": "button",
  "label": "Submit Form",
  "customAttributes": {
    "aria-label": "Submit the login form",
    "role": "button"
  }
}
```

#### 2. Color Contrast

Ensure sufficient contrast ratios:
- Normal text: 4.5:1 minimum
- Large text: 3:1 minimum

#### 3. Focus States

```json
{
  "css": ".dsl-button:focus { outline: 2px solid #007bff; outline-offset: 2px; }"
}
```

---

## Performance Optimization

### Rendering Performance

#### 1. Canvas Size Optimization

```json
// Optimal sizes for different use cases
{
  "mobile": {"width": 375, "height": 667},
  "tablet": {"width": 768, "height": 1024},
  "desktop": {"width": 1200, "height": 800},
  "thumbnail": {"width": 400, "height": 300}
}
```

#### 2. Async Rendering

Use async mode for complex layouts:

```bash
# Submit async render
curl -X POST http://localhost:8000/render/async \
  -H "Content-Type: application/json" \
  -d @complex-dashboard.json

# Check status
curl http://localhost:8000/status/task_12345
```

#### 3. Browser Optimization

```json
{
  "options": {
    "device_scale_factor": 1.0,  // Lower for faster rendering
    "wait_for_load": true,       // Ensure complete rendering
    "optimize_png": true,        // Reduce file size
    "timeout": 30               // Prevent hanging
  }
}
```

### Memory Management

#### 1. Element Limits

- **Simple layouts**: < 50 elements
- **Medium complexity**: < 100 elements  
- **Complex layouts**: < 200 elements (use async)

#### 2. Image Optimization

```json
{
  "type": "image",
  "src": "https://example.com/image.jpg",
  "style": {
    "width": "200px",
    "height": "150px",
    "objectFit": "cover"  // Prevent layout shift
  }
}
```

### Caching Strategies

#### 1. Content-Based Caching

The system automatically caches based on DSL content hash:

```json
{
  "metadata": {
    "cache_key": "custom-key",  // Optional custom cache key
    "cache_ttl": 3600          // Cache time in seconds
  }
}
```

#### 2. Template Reuse

Create reusable element templates:

```json
{
  "templates": {
    "primaryButton": {
      "type": "button",
      "style": {
        "background": "#007bff",
        "color": "white",
        "borderRadius": "8px",
        "padding": "12px 24px"
      }
    }
  }
}
```

---

## Common Use Cases

### 1. Wireframing

Create low-fidelity wireframes:

```json
{
  "title": "App Wireframe",
  "width": 375,
  "height": 667,
  "elements": [
    {
      "type": "container",
      "style": {
        "background": "#f5f5f5",
        "border": "2px dashed #ccc"
      },
      "children": [
        {
          "type": "text",
          "text": "[Navigation Bar]",
          "style": {"textAlign": "center", "color": "#666"}
        }
      ]
    }
  ]
}
```

### 2. UI Component Documentation

Document design system components:

```json
{
  "title": "Button Component States",
  "width": 800,
  "height": 300,
  "elements": [
    {
      "type": "flex",
      "style": {"display": "flex", "gap": "16px"},
      "children": [
        {
          "type": "button",
          "label": "Default",
          "style": {"background": "#007bff"}
        },
        {
          "type": "button", 
          "label": "Hover",
          "style": {"background": "#0056b3"}
        },
        {
          "type": "button",
          "label": "Disabled",
          "style": {"background": "#6c757d", "opacity": 0.6}
        }
      ]
    }
  ]
}
```

### 3. A/B Testing Mockups

Create variations for testing:

```json
{
  "title": "CTA Button Test - Variant A",
  "elements": [
    {
      "type": "button",
      "label": "Sign Up Now",
      "style": {"background": "#28a745", "color": "white"}
    }
  ]
}
```

### 4. Client Presentations

Professional mockups for client review:

```json
{
  "title": "Homepage Concept",
  "width": 1200,
  "height": 800,
  "elements": [
    {
      "type": "navbar",
      "style": {"background": "#fff", "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"}
    },
    {
      "type": "container",
      "className": "hero-section",
      "style": {
        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "color": "white",
        "padding": "60px 40px"
      }
    }
  ]
}
```

---

## Troubleshooting

### Common Issues

#### 1. Elements Not Visible

**Problem**: Elements appear outside the canvas
**Solution**: Check layout coordinates

```json
{
  "canvas": {"width": 400, "height": 300},
  "element": {
    "layout": {"x": 500, "y": 200}  // Outside canvas!
  }
}
```

#### 2. Text Overflow

**Problem**: Text gets cut off
**Solution**: Increase container size or use text wrapping

```json
{
  "type": "text",
  "text": "Very long text that might overflow",
  "layout": {"width": 300, "height": 100},  // Adequate size
  "style": {
    "wordWrap": "break-word",
    "overflow": "hidden"
  }
}
```

#### 3. Poor Performance

**Problem**: Slow rendering
**Solutions**:
- Reduce element count
- Use async rendering
- Optimize images
- Simplify layouts

#### 4. CSS Conflicts

**Problem**: Styles not applying correctly
**Solution**: Use specific selectors

```css
/* Good: Specific selector */
.dsl-button.primary { background: #007bff; }

/* Avoid: Generic selector */
button { background: #007bff; }
```

### Validation Errors

#### Common DSL Errors

1. **Missing required fields**:
   ```json
   {
     "type": "button"
     // Missing: label or text content
   }
   ```

2. **Invalid element hierarchy**:
   ```json
   {
     "type": "input",  // Cannot have children
     "children": [...]  // Error!
   }
   ```

3. **Invalid coordinates**:
   ```json
   {
     "layout": {
       "x": -10,  // Negative coordinates
       "width": 0  // Zero dimensions
     }
   }
   ```

### Getting Help

#### 1. Validation First

Always validate your DSL before rendering:

```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d @your-dsl.json
```

#### 2. Check Server Logs

Monitor server logs for detailed error information:

```bash
docker logs dsl-png-server --follow
```

#### 3. Use Examples

Start with working examples and modify incrementally:
- [`examples/simple_button.json`](../examples/simple_button.json)
- [`examples/login_form.json`](../examples/login_form.json)
- [`examples/dashboard.json`](../examples/dashboard.json)

---

## Next Steps

- **Advanced Topics**: See [DSL Reference](./DSL_REFERENCE.md) for complete syntax
- **Integration**: Check [API Documentation](./API.md) for programmatic usage
- **Production**: Review [Operations Guide](./OPERATIONS.md) for deployment
- **Examples**: Explore [Examples](./examples/) for real-world implementations

Happy designing! 🎨