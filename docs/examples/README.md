# Examples and Tutorials

Comprehensive collection of DSL to PNG examples and step-by-step tutorials demonstrating all features and capabilities of the system.

## Table of Contents

- [Quick Start Examples](#quick-start-examples)
- [Step-by-Step Tutorials](#step-by-step-tutorials)
- [Advanced Examples](#advanced-examples)
- [Integration Examples](#integration-examples)
- [Best Practices](#best-practices)
- [Performance Optimization](#performance-optimization)
- [Real-World Projects](#real-world-projects)

---

## Quick Start Examples

### Basic Button
The simplest possible DSL document with a single button.

```json
{
  "width": 300,
  "height": 150,
  "elements": [
    {
      "type": "button",
      "layout": {"x": 100, "y": 50, "width": 100, "height": 50},
      "style": {"background": "#007bff", "color": "white"},
      "label": "Click Me"
    }
  ]
}
```

**Try it:**
```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d @docs/examples/basic-button.json \
  --output basic-button.png
```

### Simple Text
Display formatted text with custom styling.

```json
{
  "width": 400,
  "height": 200,
  "elements": [
    {
      "type": "text",
      "text": "Hello, DSL World!",
      "layout": {"x": 50, "y": 80, "width": 300, "height": 40},
      "style": {
        "fontSize": 24,
        "fontWeight": "bold",
        "color": "#333333",
        "textAlign": "center"
      }
    }
  ]
}
```

### Input Field
Basic form input with placeholder text.

```json
{
  "width": 350,
  "height": 100,
  "elements": [
    {
      "type": "input",
      "placeholder": "Enter your name",
      "layout": {"x": 25, "y": 25, "width": 300, "height": 50},
      "style": {
        "fontSize": 16,
        "padding": "12px",
        "border": "2px solid #ccc",
        "borderRadius": "8px"
      }
    }
  ]
}
```

---

## Step-by-Step Tutorials

### Tutorial 1: Building Your First UI Component

**Goal:** Create a styled button with hover effects.

#### Step 1: Basic Structure
Start with the minimal DSL structure:

```json
{
  "title": "My First Button",
  "width": 300,
  "height": 150,
  "elements": []
}
```

#### Step 2: Add the Button Element
```json
{
  "title": "My First Button",
  "width": 300,
  "height": 150,
  "elements": [
    {
      "type": "button",
      "id": "primary-btn",
      "label": "Get Started"
    }
  ]
}
```

#### Step 3: Position the Button
```json
{
  "elements": [
    {
      "type": "button",
      "id": "primary-btn",
      "label": "Get Started",
      "layout": {
        "x": 100,
        "y": 50,
        "width": 100,
        "height": 50
      }
    }
  ]
}
```

#### Step 4: Style the Button
```json
{
  "elements": [
    {
      "type": "button",
      "id": "primary-btn",
      "label": "Get Started",
      "layout": {
        "x": 100,
        "y": 50,
        "width": 100,
        "height": 50
      },
      "style": {
        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "color": "white",
        "fontSize": 16,
        "fontWeight": "600",
        "borderRadius": "25px",
        "border": "none",
        "boxShadow": "0 4px 15px rgba(102, 126, 234, 0.3)"
      }
    }
  ]
}
```

#### Step 5: Add Hover Effects
```json
{
  "css": ".dsl-button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4); transition: all 0.3s ease; }",
  "elements": [...]
}
```

**[Complete Example](./tutorials/button-tutorial.json)**

### Tutorial 2: Creating a Login Form

**Goal:** Build a complete login form with validation styling.

#### Step 1: Container Setup
```json
{
  "title": "Login Form Tutorial",
  "width": 400,
  "height": 300,
  "elements": [
    {
      "type": "container",
      "id": "login-container",
      "layout": {"x": 50, "y": 50, "width": 300, "height": 200},
      "style": {
        "background": "#ffffff",
        "borderRadius": "12px",
        "padding": "24px",
        "boxShadow": "0 4px 20px rgba(0, 0, 0, 0.1)"
      },
      "children": []
    }
  ]
}
```

#### Step 2: Add Form Title
```json
{
  "children": [
    {
      "type": "text",
      "text": "Welcome Back",
      "layout": {"x": 0, "y": 0, "width": 252, "height": 30},
      "style": {
        "fontSize": 20,
        "fontWeight": "bold",
        "textAlign": "center",
        "color": "#333333",
        "marginBottom": "20px"
      }
    }
  ]
}
```

#### Step 3: Add Input Fields
```json
{
  "children": [
    // Title from previous step...
    {
      "type": "input",
      "placeholder": "Username",
      "layout": {"x": 0, "y": 45, "width": 252, "height": 40},
      "style": {
        "fontSize": 14,
        "padding": "10px 12px",
        "border": "2px solid #e1e5e9",
        "borderRadius": "6px",
        "marginBottom": "12px"
      }
    },
    {
      "type": "input",
      "placeholder": "Password",
      "layout": {"x": 0, "y": 97, "width": 252, "height": 40},
      "style": {
        "fontSize": 14,
        "padding": "10px 12px",
        "border": "2px solid #e1e5e9",
        "borderRadius": "6px"
      },
      "customAttributes": {"type": "password"}
    }
  ]
}
```

#### Step 4: Add Submit Button
```json
{
  "children": [
    // Previous elements...
    {
      "type": "button",
      "label": "Sign In",
      "layout": {"x": 0, "y": 149, "width": 252, "height": 45},
      "style": {
        "background": "#007bff",
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
```

#### Step 5: Add Interactive States
```json
{
  "css": "
    .dsl-input:focus {
      border-color: #007bff;
      box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
      outline: none;
    }
    .dsl-button:hover {
      background: #0056b3;
      transform: translateY(-1px);
    }
    .dsl-button:active {
      transform: translateY(0);
    }
  "
}
```

**[Complete Example](./tutorials/login-form-tutorial.json)**

### Tutorial 3: Responsive Dashboard Layout

**Goal:** Create a responsive dashboard using grid and flexbox layouts.

#### Step 1: Navigation Bar
```json
{
  "title": "Dashboard Tutorial",
  "width": 1200,
  "height": 800,
  "elements": [
    {
      "type": "navbar",
      "layout": {"x": 0, "y": 0, "width": 1200, "height": 60},
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
            "fontSize": 20,
            "fontWeight": "bold",
            "color": "#60a5fa"
          }
        }
      ]
    }
  ]
}
```

#### Step 2: Metrics Grid
```json
{
  "type": "grid",
  "id": "metrics-grid",
  "layout": {"x": 24, "y": 84, "width": 1152, "height": 200},
  "style": {
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fit, minmax(250px, 1fr))",
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
          "text": "Total Revenue",
          "style": {"fontSize": 14, "color": "#6b7280", "marginBottom": "8px"}
        },
        {
          "type": "text",
          "text": "$47,281",
          "style": {"fontSize": 28, "fontWeight": "bold", "color": "#111827"}
        }
      ]
    }
  ]
}
```

#### Step 3: Responsive Breakpoints
```json
{
  "responsiveBreakpoints": {
    "sm": 640,
    "md": 768,
    "lg": 1024,
    "xl": 1280
  },
  "elements": [
    {
      "type": "grid",
      "style": {
        "gridTemplateColumns": "repeat(4, 1fr)"
      },
      "responsive": {
        "lg": {
          "style": {"gridTemplateColumns": "repeat(3, 1fr)"}
        },
        "md": {
          "style": {"gridTemplateColumns": "repeat(2, 1fr)"}
        },
        "sm": {
          "style": {"gridTemplateColumns": "1fr"}
        }
      }
    }
  ]
}
```

**[Complete Example](./tutorials/dashboard-tutorial.json)**

---

## Advanced Examples

### Complex Component Library

Demonstrates building reusable UI components:

- **[Component Library](./advanced/component-library.json)** - Reusable button, card, and form components
- **[Design System](./advanced/design-system.json)** - Consistent colors, typography, and spacing
- **[Layout System](./advanced/layout-system.json)** - Grid and flexbox layout patterns

### E-commerce Product Page

Full-featured product page with:

- **[Product Showcase](./advanced/ecommerce-product.json)** - Image gallery, pricing, and description
- **[Shopping Cart](./advanced/shopping-cart.json)** - Interactive cart with item management
- **[Checkout Flow](./advanced/checkout-flow.json)** - Multi-step checkout process

### Mobile App Interfaces

Mobile-optimized designs:

- **[iOS App Interface](./advanced/ios-app.json)** - Native iOS design patterns
- **[Android Material Design](./advanced/android-material.json)** - Material Design components
- **[Progressive Web App](./advanced/pwa-interface.json)** - PWA-optimized layout

---

## Integration Examples

### REST API Integration

```python
# Python example using requests
import requests
import base64

def render_dsl_to_png(dsl_content, width=800, height=600):
    """Render DSL content to PNG using the API."""
    
    payload = {
        "dsl_content": dsl_content,
        "options": {
            "width": width,
            "height": height,
            "optimize_png": True
        }
    }
    
    response = requests.post(
        "http://localhost:8000/render",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result["success"]:
            # Decode base64 PNG data
            png_data = base64.b64decode(result["png_result"]["base64_data"])
            return png_data
        else:
            raise Exception(f"Rendering failed: {result['error']}")
    else:
        raise Exception(f"API request failed: {response.status_code}")

# Usage example
dsl = {
    "width": 400,
    "height": 300,
    "elements": [
        {
            "type": "text",
            "text": "Generated via API",
            "layout": {"x": 50, "y": 100, "width": 300, "height": 100},
            "style": {"fontSize": 24, "textAlign": "center"}
        }
    ]
}

png_data = render_dsl_to_png(str(dsl))
with open("api-generated.png", "wb") as f:
    f.write(png_data)
```

### MCP Client Integration

```javascript
// JavaScript MCP client example
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

async function renderWithMCP() {
    // Connect to MCP server
    const transport = new StdioClientTransport({
        command: 'python',
        args: ['-m', 'src.mcp_server.server']
    });
    
    const client = new Client(
        { name: "dsl-renderer", version: "1.0.0" },
        { capabilities: {} }
    );
    
    await client.connect(transport);
    
    // Define DSL content
    const dslContent = JSON.stringify({
        width: 500,
        height: 300,
        elements: [
            {
                type: "button",
                layout: { x: 200, y: 125, width: 100, height: 50 },
                style: { background: "#28a745", color: "white" },
                label: "MCP Button"
            }
        ]
    });
    
    // Render using MCP tool
    const result = await client.callTool("render_ui_mockup", {
        dsl_content: dslContent,
        width: 500,
        height: 300,
        async_mode: false
    });
    
    console.log("Render result:", result);
    
    await client.close();
}

renderWithMCP().catch(console.error);
```

### React Component Integration

```jsx
// React component for DSL rendering
import React, { useState, useEffect } from 'react';

const DSLRenderer = ({ dslContent, width = 800, height = 600 }) => {
    const [pngData, setPngData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    useEffect(() => {
        if (dslContent) {
            renderDSL();
        }
    }, [dslContent, width, height]);
    
    const renderDSL = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const response = await fetch('/api/render', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    dsl_content: JSON.stringify(dslContent),
                    options: { width, height }
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                setPngData(`data:image/png;base64,${result.png_result.base64_data}`);
            } else {
                setError(result.error);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };
    
    if (loading) return <div className="loading">Rendering...</div>;
    if (error) return <div className="error">Error: {error}</div>;
    if (!pngData) return <div className="placeholder">No DSL content</div>;
    
    return (
        <div className="dsl-renderer">
            <img 
                src={pngData} 
                alt="Rendered DSL" 
                style={{ maxWidth: '100%', height: 'auto' }}
            />
        </div>
    );
};

// Usage example
const App = () => {
    const sampleDSL = {
        width: 400,
        height: 200,
        elements: [
            {
                type: "text",
                text: "React Integration",
                layout: { x: 50, y: 75, width: 300, height: 50 },
                style: { fontSize: 20, textAlign: "center" }
            }
        ]
    };
    
    return (
        <div className="app">
            <h1>DSL to PNG React Demo</h1>
            <DSLRenderer dslContent={sampleDSL} />
        </div>
    );
};

export default App;
```

---

## Best Practices

### Performance Optimization

#### 1. Efficient Element Organization
```json
{
  "title": "Performance Optimized Layout",
  "width": 800,
  "height": 600,
  "elements": [
    {
      "type": "container",
      "style": {
        "display": "flex",
        "flexDirection": "column",
        "gap": "16px"
      },
      "children": [
        // Group related elements in containers
        // Use flexbox/grid instead of absolute positioning
        // Limit nesting depth to 5 levels maximum
      ]
    }
  ]
}
```

#### 2. CSS Optimization
```json
{
  "css": "
    /* Use efficient selectors */
    .card { background: white; border-radius: 8px; }
    
    /* Avoid complex animations in static renders */
    .button:hover { background: #0056b3; }
    
    /* Use CSS custom properties for consistency */
    :root {
      --primary-color: #007bff;
      --border-radius: 8px;
    }
  "
}
```

### Accessibility Guidelines

```json
{
  "elements": [
    {
      "type": "button",
      "label": "Submit Form",
      "customAttributes": {
        "aria-label": "Submit the contact form",
        "role": "button",
        "tabindex": "0"
      },
      "style": {
        "color": "#ffffff",
        "background": "#007bff"
        // Ensure 4.5:1 contrast ratio minimum
      }
    },
    {
      "type": "image",
      "src": "chart.png",
      "alt": "Monthly sales chart showing 15% growth",
      // Always provide meaningful alt text
    }
  ]
}
```

### Responsive Design Patterns

```json
{
  "responsiveBreakpoints": {
    "sm": 640,
    "md": 768,
    "lg": 1024
  },
  "elements": [
    {
      "type": "grid",
      "style": {
        "display": "grid",
        "gridTemplateColumns": "repeat(auto-fit, minmax(250px, 1fr))",
        "gap": "clamp(16px, 4vw, 32px)"
        // Use clamp() for fluid scaling
      },
      "responsive": {
        "sm": {
          "style": {
            "gridTemplateColumns": "1fr",
            "gap": "16px"
          }
        }
      }
    }
  ]
}
```

---

## Real-World Projects

### 1. Marketing Landing Page

**[View Example](./projects/landing-page.json)**

Complete marketing page featuring:
- Hero section with call-to-action
- Feature highlights with icons
- Testimonials carousel
- Contact form with validation

### 2. Admin Dashboard

**[View Example](./projects/admin-dashboard.json)**

Full admin interface including:
- Sidebar navigation
- Data tables with sorting
- Chart visualizations
- User management panels

### 3. E-learning Platform

**[View Example](./projects/elearning-platform.json)**

Educational interface with:
- Course catalog grid
- Video player interface
- Progress tracking
- Quiz components

### 4. Social Media App

**[View Example](./projects/social-media.json)**

Social platform mockup featuring:
- News feed layout
- Post creation interface
- Profile cards
- Messaging components

---

## Testing Your DSL

### Validation Checklist

Before rendering, always validate your DSL:

```bash
# 1. Validate syntax
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d @your-dsl.json

# 2. Check for common issues
- Elements within canvas bounds
- Valid element types
- Proper nesting hierarchy
- CSS syntax correctness

# 3. Test rendering
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d @your-dsl.json \
  --output test-render.png
```

### Common Pitfalls

1. **Elements Outside Canvas**
   ```json
   // Wrong: Button extends beyond canvas
   {
     "width": 400,
     "elements": [
       {
         "layout": {"x": 350, "y": 50, "width": 100, "height": 50}
         // x + width = 450 > 400 (canvas width)
       }
     ]
   }
   ```

2. **Invalid Element Hierarchy**
   ```json
   // Wrong: Input cannot have children
   {
     "type": "input",
     "children": [...]  // Invalid!
   }
   ```

3. **Poor Performance**
   ```json
   // Avoid: Too many absolutely positioned elements
   {
     "elements": [
       {"layout": {"x": 10, "y": 20}},
       {"layout": {"x": 30, "y": 40}},
       // ... 100+ more elements
     ]
   }
   
   // Better: Use containers and flexbox
   {
     "elements": [
       {
         "type": "flex",
         "style": {"display": "flex", "flexWrap": "wrap", "gap": "16px"},
         "children": [...]
       }
     ]
   }
   ```

---

## Getting Help

- **Documentation**: [Complete DSL Reference](../DSL_REFERENCE.md)
- **API Guide**: [API Documentation](../API.md)
- **Troubleshooting**: [Common Issues](../TROUBLESHOOTING.md)
- **Community**: [GitHub Discussions](https://github.com/your-org/dslToPngMCP/discussions)

Happy designing! 🎨