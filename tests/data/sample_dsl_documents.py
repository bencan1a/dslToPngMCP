"""
Sample DSL Documents
===================

Collection of sample DSL documents for testing various scenarios,
from simple basic layouts to complex responsive designs.
"""

# Simple DSL Documents
SIMPLE_TEXT_DOCUMENT = {
    "title": "Simple Text Example",
    "viewport": {"width": 800, "height": 600},
    "elements": [
        {
            "type": "text",
            "content": "Hello, World!",
            "style": {
                "fontSize": "24px",
                "color": "#333333",
                "textAlign": "center",
                "marginTop": "50px"
            }
        }
    ]
}

SIMPLE_LAYOUT_DOCUMENT = {
    "title": "Simple Layout Example",
    "viewport": {"width": 1024, "height": 768},
    "elements": [
        {
            "type": "container",
            "style": {
                "width": "100%",
                "height": "100px",
                "backgroundColor": "#f0f0f0",
                "padding": "20px"
            },
            "children": [
                {
                    "type": "text",
                    "content": "Header Section",
                    "style": {"fontSize": "32px", "fontWeight": "bold"}
                }
            ]
        },
        {
            "type": "container",
            "style": {
                "width": "100%",
                "height": "400px",
                "display": "flex",
                "flexDirection": "row"
            },
            "children": [
                {
                    "type": "container",
                    "style": {
                        "flex": "1",
                        "backgroundColor": "#e8f4f8",
                        "padding": "20px"
                    },
                    "children": [
                        {
                            "type": "text",
                            "content": "Left Sidebar",
                            "style": {"fontSize": "18px"}
                        }
                    ]
                },
                {
                    "type": "container",
                    "style": {
                        "flex": "3",
                        "backgroundColor": "#ffffff",
                        "padding": "20px"
                    },
                    "children": [
                        {
                            "type": "text",
                            "content": "Main Content Area",
                            "style": {"fontSize": "20px", "lineHeight": "1.6"}
                        }
                    ]
                }
            ]
        }
    ]
}

# Complex DSL Documents
COMPLEX_DASHBOARD_DOCUMENT = {
    "title": "Dashboard Example",
    "viewport": {"width": 1440, "height": 900},
    "theme": {
        "primaryColor": "#2563eb",
        "secondaryColor": "#64748b",
        "backgroundColor": "#f8fafc",
        "textColor": "#1e293b"
    },
    "elements": [
        {
            "type": "container",
            "id": "header",
            "style": {
                "width": "100%",
                "height": "80px",
                "backgroundColor": "{theme.primaryColor}",
                "color": "white",
                "display": "flex",
                "alignItems": "center",
                "padding": "0 24px",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
            },
            "children": [
                {
                    "type": "text",
                    "content": "Analytics Dashboard",
                    "style": {
                        "fontSize": "24px",
                        "fontWeight": "600"
                    }
                }
            ]
        },
        {
            "type": "container",
            "id": "main-content",
            "style": {
                "width": "100%",
                "height": "calc(100vh - 80px)",
                "display": "grid",
                "gridTemplateColumns": "250px 1fr",
                "gridTemplateRows": "1fr"
            },
            "children": [
                {
                    "type": "container",
                    "id": "sidebar",
                    "style": {
                        "backgroundColor": "white",
                        "borderRight": "1px solid #e2e8f0",
                        "padding": "24px"
                    },
                    "children": [
                        {
                            "type": "text",
                            "content": "Navigation",
                            "style": {
                                "fontSize": "16px",
                                "fontWeight": "600",
                                "marginBottom": "16px"
                            }
                        },
                        {
                            "type": "list",
                            "items": [
                                {"text": "Overview", "active": True},
                                {"text": "Analytics"},
                                {"text": "Reports"},
                                {"text": "Settings"}
                            ],
                            "style": {
                                "listStyle": "none",
                                "padding": "0"
                            }
                        }
                    ]
                },
                {
                    "type": "container",
                    "id": "dashboard-content",
                    "style": {
                        "padding": "24px",
                        "backgroundColor": "{theme.backgroundColor}"
                    },
                    "children": [
                        {
                            "type": "container",
                            "id": "metrics-grid",
                            "style": {
                                "display": "grid",
                                "gridTemplateColumns": "repeat(auto-fit, minmax(250px, 1fr))",
                                "gap": "24px",
                                "marginBottom": "32px"
                            },
                            "children": [
                                {
                                    "type": "card",
                                    "content": {
                                        "title": "Total Users",
                                        "value": "12,345",
                                        "change": "+12%"
                                    },
                                    "style": {
                                        "backgroundColor": "white",
                                        "borderRadius": "8px",
                                        "padding": "24px",
                                        "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"
                                    }
                                },
                                {
                                    "type": "card",
                                    "content": {
                                        "title": "Revenue",
                                        "value": "$45,678",
                                        "change": "+8%"
                                    },
                                    "style": {
                                        "backgroundColor": "white",
                                        "borderRadius": "8px",
                                        "padding": "24px",
                                        "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"
                                    }
                                },
                                {
                                    "type": "card",
                                    "content": {
                                        "title": "Conversion Rate",
                                        "value": "3.24%",
                                        "change": "+0.8%"
                                    },
                                    "style": {
                                        "backgroundColor": "white",
                                        "borderRadius": "8px",
                                        "padding": "24px",
                                        "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"
                                    }
                                }
                            ]
                        },
                        {
                            "type": "container",
                            "id": "charts-section",
                            "style": {
                                "display": "grid",
                                "gridTemplateColumns": "2fr 1fr",
                                "gap": "24px"
                            },
                            "children": [
                                {
                                    "type": "chart",
                                    "chartType": "line",
                                    "data": {
                                        "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                                        "datasets": [
                                            {
                                                "label": "Revenue",
                                                "data": [12000, 15000, 13000, 17000, 16000, 19000]
                                            }
                                        ]
                                    },
                                    "style": {
                                        "backgroundColor": "white",
                                        "borderRadius": "8px",
                                        "padding": "24px",
                                        "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"
                                    }
                                },
                                {
                                    "type": "chart",
                                    "chartType": "doughnut",
                                    "data": {
                                        "labels": ["Desktop", "Mobile", "Tablet"],
                                        "datasets": [
                                            {
                                                "data": [65, 28, 7],
                                                "backgroundColor": ["#2563eb", "#64748b", "#94a3b8"]
                                            }
                                        ]
                                    },
                                    "style": {
                                        "backgroundColor": "white",
                                        "borderRadius": "8px",
                                        "padding": "24px",
                                        "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}

RESPONSIVE_DESIGN_DOCUMENT = {
    "title": "Responsive Design Example",
    "viewport": {"width": 1200, "height": 800},
    "responsive": {
        "breakpoints": {
            "mobile": "768px",
            "tablet": "1024px",
            "desktop": "1200px"
        }
    },
    "elements": [
        {
            "type": "container",
            "id": "hero-section",
            "style": {
                "width": "100%",
                "height": "400px",
                "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "color": "white",
                "textAlign": "center"
            },
            "responsive": {
                "mobile": {
                    "height": "300px",
                    "padding": "20px"
                },
                "tablet": {
                    "height": "350px"
                }
            },
            "children": [
                {
                    "type": "container",
                    "children": [
                        {
                            "type": "text",
                            "content": "Welcome to Our Platform",
                            "style": {
                                "fontSize": "48px",
                                "fontWeight": "700",
                                "marginBottom": "16px"
                            },
                            "responsive": {
                                "mobile": {
                                    "fontSize": "32px"
                                },
                                "tablet": {
                                    "fontSize": "40px"
                                }
                            }
                        },
                        {
                            "type": "text",
                            "content": "Build amazing experiences with our tools",
                            "style": {
                                "fontSize": "20px",
                                "opacity": "0.9"
                            },
                            "responsive": {
                                "mobile": {
                                    "fontSize": "16px"
                                }
                            }
                        }
                    ]
                }
            ]
        },
        {
            "type": "container",
            "id": "features-section",
            "style": {
                "padding": "80px 40px",
                "backgroundColor": "#f8fafc"
            },
            "responsive": {
                "mobile": {
                    "padding": "40px 20px"
                }
            },
            "children": [
                {
                    "type": "text",
                    "content": "Key Features",
                    "style": {
                        "fontSize": "36px",
                        "fontWeight": "600",
                        "textAlign": "center",
                        "marginBottom": "48px",
                        "color": "#1e293b"
                    }
                },
                {
                    "type": "container",
                    "style": {
                        "display": "grid",
                        "gridTemplateColumns": "repeat(auto-fit, minmax(300px, 1fr))",
                        "gap": "32px",
                        "maxWidth": "1200px",
                        "margin": "0 auto"
                    },
                    "responsive": {
                        "mobile": {
                            "gridTemplateColumns": "1fr",
                            "gap": "24px"
                        }
                    },
                    "children": [
                        {
                            "type": "card",
                            "content": {
                                "icon": "🚀",
                                "title": "Fast Performance",
                                "description": "Lightning-fast rendering with optimized algorithms"
                            },
                            "style": {
                                "backgroundColor": "white",
                                "borderRadius": "12px",
                                "padding": "32px",
                                "textAlign": "center",
                                "boxShadow": "0 4px 6px rgba(0,0,0,0.1)"
                            }
                        },
                        {
                            "type": "card",
                            "content": {
                                "icon": "🎨",
                                "title": "Beautiful Design",
                                "description": "Stunning visuals with customizable themes"
                            },
                            "style": {
                                "backgroundColor": "white",
                                "borderRadius": "12px",
                                "padding": "32px",
                                "textAlign": "center",
                                "boxShadow": "0 4px 6px rgba(0,0,0,0.1)"
                            }
                        },
                        {
                            "type": "card",
                            "content": {
                                "icon": "⚡",
                                "title": "Easy Integration",
                                "description": "Simple API for seamless integration"
                            },
                            "style": {
                                "backgroundColor": "white",
                                "borderRadius": "12px",
                                "padding": "32px",
                                "textAlign": "center",
                                "boxShadow": "0 4px 6px rgba(0,0,0,0.1)"
                            }
                        }
                    ]
                }
            ]
        }
    ]
}

# Error Test Cases
INVALID_STRUCTURE_DOCUMENT = {
    "title": "Invalid Structure Test",
    # Missing viewport
    "elements": [
        {
            "type": "unknown_element",  # Invalid element type
            "content": "This should cause validation errors"
        }
    ]
}

MALFORMED_STYLE_DOCUMENT = {
    "title": "Malformed Style Test",
    "viewport": {"width": 800, "height": 600},
    "elements": [
        {
            "type": "text",
            "content": "Test content",
            "style": {
                "fontSize": "invalid-size",  # Invalid CSS value
                "color": "not-a-color",     # Invalid color
                "margin": "definitely-not-valid"  # Invalid margin
            }
        }
    ]
}

# Performance Test Documents
LARGE_DOCUMENT_FOR_PERFORMANCE = {
    "title": "Large Document for Performance Testing",
    "viewport": {"width": 1920, "height": 1080},
    "elements": [
        {
            "type": "container",
            "style": {
                "display": "grid",
                "gridTemplateColumns": "repeat(10, 1fr)",
                "gap": "10px",
                "padding": "20px"
            },
            "children": [
                {
                    "type": "text",
                    "content": f"Item {i}",
                    "style": {
                        "backgroundColor": f"hsl({i * 36}, 70%, 80%)",
                        "padding": "20px",
                        "borderRadius": "8px",
                        "textAlign": "center",
                        "fontSize": "14px"
                    }
                }
                for i in range(100)  # 100 items for performance testing
            ]
        }
    ]
}

DEEPLY_NESTED_DOCUMENT = {
    "title": "Deeply Nested Document",
    "viewport": {"width": 800, "height": 600},
    "elements": []
}

def create_deeply_nested_elements(depth=10):
    """Create deeply nested elements for testing."""
    if depth <= 0:
        return {
            "type": "text",
            "content": f"Nested level {depth}",
            "style": {"fontSize": "12px", "padding": "5px"}
        }
    
    return {
        "type": "container",
        "style": {
            "border": "1px solid #ccc",
            "padding": "10px",
            "margin": "5px"
        },
        "children": [create_deeply_nested_elements(depth - 1)]
    }

# Add the deeply nested element
DEEPLY_NESTED_DOCUMENT["elements"] = [create_deeply_nested_elements(15)]

# Edge Case Documents
EMPTY_DOCUMENT = {
    "title": "Empty Document",
    "viewport": {"width": 800, "height": 600},
    "elements": []
}

MINIMAL_DOCUMENT = {
    "title": "Minimal Document",
    "viewport": {"width": 100, "height": 100},
    "elements": [
        {
            "type": "text",
            "content": "."
        }
    ]
}

MAXIMUM_SIZE_DOCUMENT = {
    "title": "Maximum Size Document",
    "viewport": {"width": 4096, "height": 4096},
    "elements": [
        {
            "type": "container",
            "style": {
                "width": "100%",
                "height": "100%",
                "backgroundColor": "#f0f0f0"
            },
            "children": [
                {
                    "type": "text",
                    "content": "Maximum size test",
                    "style": {
                        "fontSize": "48px",
                        "textAlign": "center",
                        "marginTop": "50%"
                    }
                }
            ]
        }
    ]
}

# Specialized Test Documents
FORM_DOCUMENT = {
    "title": "Form Example",
    "viewport": {"width": 800, "height": 1000},
    "elements": [
        {
            "type": "container",
            "style": {
                "maxWidth": "600px",
                "margin": "0 auto",
                "padding": "40px"
            },
            "children": [
                {
                    "type": "text",
                    "content": "Contact Form",
                    "style": {
                        "fontSize": "32px",
                        "fontWeight": "600",
                        "marginBottom": "32px",
                        "textAlign": "center"
                    }
                },
                {
                    "type": "form",
                    "fields": [
                        {
                            "type": "input",
                            "label": "Full Name",
                            "placeholder": "Enter your full name",
                            "required": True
                        },
                        {
                            "type": "input",
                            "label": "Email",
                            "placeholder": "Enter your email",
                            "inputType": "email",
                            "required": True
                        },
                        {
                            "type": "textarea",
                            "label": "Message",
                            "placeholder": "Enter your message",
                            "rows": 4,
                            "required": True
                        },
                        {
                            "type": "button",
                            "text": "Send Message",
                            "buttonType": "submit",
                            "style": {
                                "backgroundColor": "#2563eb",
                                "color": "white",
                                "padding": "12px 24px",
                                "border": "none",
                                "borderRadius": "6px",
                                "fontSize": "16px",
                                "cursor": "pointer"
                            }
                        }
                    ]
                }
            ]
        }
    ]
}

TABLE_DOCUMENT = {
    "title": "Table Example",
    "viewport": {"width": 1200, "height": 800},
    "elements": [
        {
            "type": "container",
            "style": {
                "padding": "40px"
            },
            "children": [
                {
                    "type": "text",
                    "content": "Sales Report",
                    "style": {
                        "fontSize": "28px",
                        "fontWeight": "600",
                        "marginBottom": "24px"
                    }
                },
                {
                    "type": "table",
                    "headers": ["Product", "Units Sold", "Revenue", "Growth"],
                    "rows": [
                        ["Product A", "1,234", "$12,340", "+12%"],
                        ["Product B", "987", "$9,870", "+8%"],
                        ["Product C", "1,456", "$14,560", "+15%"],
                        ["Product D", "789", "$7,890", "-3%"],
                        ["Product E", "2,123", "$21,230", "+22%"]
                    ],
                    "style": {
                        "width": "100%",
                        "borderCollapse": "collapse",
                        "border": "1px solid #e5e7eb"
                    },
                    "headerStyle": {
                        "backgroundColor": "#f9fafb",
                        "fontWeight": "600",
                        "padding": "12px",
                        "borderBottom": "2px solid #e5e7eb"
                    },
                    "cellStyle": {
                        "padding": "12px",
                        "borderBottom": "1px solid #e5e7eb"
                    }
                }
            ]
        }
    ]
}

# Animation and Interactive Elements
ANIMATED_DOCUMENT = {
    "title": "Animated Elements",
    "viewport": {"width": 800, "height": 600},
    "elements": [
        {
            "type": "container",
            "style": {
                "display": "flex",
                "justifyContent": "space-around",
                "alignItems": "center",
                "height": "100%",
                "backgroundColor": "#1e293b"
            },
            "children": [
                {
                    "type": "text",
                    "content": "Animated Text",
                    "style": {
                        "fontSize": "32px",
                        "color": "white",
                        "animation": "fadeIn 2s ease-in-out"
                    }
                },
                {
                    "type": "container",
                    "style": {
                        "width": "100px",
                        "height": "100px",
                        "backgroundColor": "#3b82f6",
                        "borderRadius": "50%",
                        "animation": "bounce 1s infinite"
                    }
                },
                {
                    "type": "container",
                    "style": {
                        "width": "80px",
                        "height": "80px",
                        "backgroundColor": "#ef4444",
                        "animation": "spin 3s linear infinite"
                    }
                }
            ]
        }
    ],
    "animations": {
        "fadeIn": {
            "from": {"opacity": 0},
            "to": {"opacity": 1}
        },
        "bounce": {
            "0%, 20%, 50%, 80%, 100%": {"transform": "translateY(0)"},
            "40%": {"transform": "translateY(-30px)"},
            "60%": {"transform": "translateY(-15px)"}
        },
        "spin": {
            "from": {"transform": "rotate(0deg)"},
            "to": {"transform": "rotate(360deg)"}
        }
    }
}

# Collection of all test documents
ALL_TEST_DOCUMENTS = {
    "simple": {
        "text": SIMPLE_TEXT_DOCUMENT,
        "layout": SIMPLE_LAYOUT_DOCUMENT
    },
    "complex": {
        "dashboard": COMPLEX_DASHBOARD_DOCUMENT,
        "responsive": RESPONSIVE_DESIGN_DOCUMENT
    },
    "invalid": {
        "structure": INVALID_STRUCTURE_DOCUMENT,
        "style": MALFORMED_STYLE_DOCUMENT
    },
    "performance": {
        "large": LARGE_DOCUMENT_FOR_PERFORMANCE,
        "nested": DEEPLY_NESTED_DOCUMENT
    },
    "edge_cases": {
        "empty": EMPTY_DOCUMENT,
        "minimal": MINIMAL_DOCUMENT,
        "maximum": MAXIMUM_SIZE_DOCUMENT
    },
    "specialized": {
        "form": FORM_DOCUMENT,
        "table": TABLE_DOCUMENT,
        "animated": ANIMATED_DOCUMENT
    }
}

def get_test_document(category, name):
    """Get a specific test document by category and name."""
    return ALL_TEST_DOCUMENTS.get(category, {}).get(name)

def get_all_valid_documents():
    """Get all valid test documents (excluding invalid ones)."""
    valid_docs = {}
    for category, docs in ALL_TEST_DOCUMENTS.items():
        if category != "invalid":
            valid_docs.update(docs)
    return valid_docs

def get_invalid_documents():
    """Get all invalid test documents for error testing."""
    return ALL_TEST_DOCUMENTS.get("invalid", {})