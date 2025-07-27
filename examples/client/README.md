# MCP SSE Client Library

A comprehensive JavaScript/TypeScript client library for connecting to DSL to PNG MCP Server via Server-Sent Events (SSE). Provides real-time progress updates, robust error handling, and an intuitive API for DSL validation and PNG rendering.

## 🚀 Features

- **Real-time Progress Updates**: Monitor DSL rendering progress with live SSE events
- **TypeScript Support**: Full type safety with comprehensive TypeScript definitions
- **Automatic Reconnection**: Robust connection management with exponential backoff
- **Error Recovery**: Comprehensive error handling with detailed error codes
- **Rate Limiting Awareness**: Built-in handling of rate limiting with appropriate delays
- **Authentication Support**: API key-based authentication for secure connections
- **Cross-browser Compatible**: Works on modern browsers (Chrome 60+, Firefox 55+, Safari 12+)
- **Production Ready**: Comprehensive logging, debugging, and monitoring capabilities

## 📦 Installation

### Option 1: Direct Download
Download the library files and include them in your project:

```html
<script type="module">
  import MCPSSEClient from './lib/mcp-sse-client.js';
  // Your code here
</script>
```

### Option 2: npm Package (Future)
```bash
npm install @dsl-to-png/mcp-sse-client
```

## 🎯 Quick Start

### Basic Usage

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MCP SSE Client Example</title>
</head>
<body>
    <script type="module">
        import MCPSSEClient from './lib/mcp-sse-client.js';

        // Create client instance
        const client = new MCPSSEClient('http://localhost:8000', 'your-api-key');

        // Set up event listeners
        client.addEventListener('renderProgress', (event) => {
            console.log(`Progress: ${event.detail.progress}% - ${event.detail.message}`);
        });

        client.addEventListener('renderCompleted', (event) => {
            const img = document.createElement('img');
            img.src = `data:image/png;base64,${event.detail.result.base64Data}`;
            document.body.appendChild(img);
        });

        // Connect and render
        async function main() {
            await client.connect();
            
            const result = await client.renderUIMarkup({
                dsl_content: JSON.stringify({
                    type: 'button',
                    text: 'Hello World',
                    style: { backgroundColor: 'blue', color: 'white' }
                }),
                options: { width: 800, height: 600 }
            });

            console.log('Render completed:', result);
        }

        main().catch(console.error);
    </script>
</body>
</html>
```

### TypeScript Usage

```typescript
import MCPSSEClient, { RenderRequest, RenderResult } from './lib/mcp-sse-client.js';
import { ProgressEventData } from './lib/types.js';

const client = new MCPSSEClient('http://localhost:8000', 'your-api-key', {
    debug: true,
    maxReconnectAttempts: 10
});

client.addEventListener('renderProgress', (event: CustomEvent<ProgressEventData>) => {
    console.log(`Progress: ${event.detail.progress}%`);
});

const request: RenderRequest = {
    dsl_content: JSON.stringify({ type: 'button', text: 'Click me' }),
    options: { width: 800, height: 600 }
};

const result: RenderResult = await client.renderUIMarkup(request);
```

## 🛠️ API Overview

### Core Methods

#### `new MCPSSEClient(baseUrl, apiKey?, config?)`
Creates a new MCP SSE client instance.

```javascript
const client = new MCPSSEClient('http://localhost:8000', 'api-key', {
    debug: true,
    reconnectInterval: 2000,
    maxReconnectAttempts: 5
});
```

#### `connect(): Promise<void>`
Establishes SSE connection to the server.

```javascript
await client.connect();
```

#### `disconnect(): void`
Closes the SSE connection.

```javascript
client.disconnect();
```

#### `renderUIMarkup(request, options?): Promise<RenderResult>`
Renders DSL content to PNG with real-time progress updates.

```javascript
const result = await client.renderUIMarkup({
    dsl_content: '{"type": "button", "text": "Hello"}',
    options: { width: 800, height: 600 },
    async_mode: false
});
```

#### `validateDSL(request, options?): Promise<ValidationResult>`
Validates DSL content without rendering.

```javascript
const result = await client.validateDSL({
    dsl_content: '{"type": "button", "text": "Hello"}',
    options: { strict: true }
});
```

#### `getRenderStatus(request, options?): Promise<TaskStatusResult>`
Gets the status of an async rendering task.

```javascript
const status = await client.getRenderStatus({
    task_id: 'task_123',
    include_result: true
});
```

### Event Handling

The client extends `EventTarget` and emits various events:

```javascript
// Connection events
client.addEventListener('connectionOpened', (event) => {
    console.log('Connected:', event.detail.connection_id);
});

client.addEventListener('connectionClosed', (event) => {
    console.log('Disconnected:', event.detail.reason);
});

// Progress events
client.addEventListener('renderProgress', (event) => {
    const { progress, message, stage } = event.detail;
    updateProgressBar(progress, message);
});

// Completion events
client.addEventListener('renderCompleted', (event) => {
    displayResult(event.detail.result);
});

client.addEventListener('renderFailed', (event) => {
    showError(event.detail.error);
});

// Rate limiting
client.addEventListener('rateLimitWarning', (event) => {
    console.warn('Rate limit warning:', event.detail);
});
```

## 🎨 Demo Applications

The library includes three comprehensive demo applications:

### Basic Demo (`demo-basic.html`)
- Simple DSL rendering interface
- Real-time progress tracking
- Connection management
- Sample DSL templates

### Advanced Demo (`demo-advanced.html`)
- Multiple concurrent renders
- Batch processing
- Advanced configuration options
- Performance monitoring

### Validation Demo (`demo-validation.html`)
- DSL validation without rendering
- Syntax highlighting
- Error reporting and suggestions
- Real-time validation feedback

## 🔧 Configuration Options

```javascript
const config = {
    // Connection settings
    reconnectInterval: 1000,        // Initial reconnect delay (ms)
    maxReconnectAttempts: 5,        // Max reconnection attempts
    reconnectExponentialBase: 2,    // Exponential backoff multiplier
    
    // Timeout settings
    heartbeatTimeout: 60000,        // Heartbeat timeout (ms)
    requestTimeout: 30000,          // Request timeout (ms)
    connectionTimeout: 10000,       // Connection timeout (ms)
    
    // Debug options
    debug: false                    // Enable debug logging
};

const client = new MCPSSEClient(baseUrl, apiKey, config);
```

## 🎯 Advanced Usage

### Progress Tracking with UI Components

```javascript
import { ProgressBar, EventLogger } from './js/demo-utils.js';

// Create UI components
const progressBar = new ProgressBar(document.getElementById('progress'));
const eventLogger = new EventLogger(document.getElementById('events'));

// Setup automatic logging
setupClientLogging(client, eventLogger);

// Custom progress handling
client.addEventListener('renderProgress', (event) => {
    const { progress, message, stage, estimated_remaining } = event.detail;
    progressBar.update(progress, message, stage, estimated_remaining);
});
```

### Error Handling and Recovery

```javascript
client.addEventListener('error', (event) => {
    const { code, message, details } = event.detail;
    
    switch (code) {
        case 'CONNECTION_FAILED':
            showConnectionError(message);
            break;
        case 'AUTHENTICATION_FAILED':
            promptForNewApiKey();
            break;
        case 'RATE_LIMIT_EXCEEDED':
            showRateLimitNotification(details);
            break;
        default:
            showGenericError(message);
    }
});
```

### Multiple Concurrent Renders

```javascript
const tasks = [
    client.renderUIMarkup({ dsl_content: dsl1 }),
    client.renderUIMarkup({ dsl_content: dsl2 }),
    client.renderUIMarkup({ dsl_content: dsl3 })
];

try {
    const results = await Promise.allSettled(tasks);
    results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
            displayResult(result.value, index);
        } else {
            showError(result.reason, index);
        }
    });
} catch (error) {
    console.error('Batch render failed:', error);
}
```

### Custom Event Handlers

```javascript
class MyRenderHandler {
    constructor(client) {
        this.client = client;
        this.setupHandlers();
    }
    
    setupHandlers() {
        this.client.addEventListener('renderProgress', this.onProgress.bind(this));
        this.client.addEventListener('renderCompleted', this.onCompleted.bind(this));
    }
    
    onProgress(event) {
        const { progress, stage } = event.detail;
        this.updateUI(progress, stage);
    }
    
    onCompleted(event) {
        this.displayResult(event.detail.result);
        this.sendAnalytics('render_completed', event.detail);
    }
}
```

## 🔍 Debugging and Monitoring

### Enable Debug Mode

```javascript
const client = new MCPSSEClient(baseUrl, apiKey, { debug: true });
```

### Monitor Connection State

```javascript
console.log('Connection state:', client.state);
console.log('Is connected:', client.isConnected);
console.log('Connection ID:', client.id);
console.log('Active requests:', client.activeRequestCount);
console.log('Reconnect attempts:', client.reconnectCount);
```

### Custom Logging

```javascript
client.addEventListener('connectionStateChanged', (event) => {
    analytics.track('connection_state_change', {
        from: event.detail.oldState,
        to: event.detail.newState,
        connectionId: client.id
    });
});
```

## 🌐 Browser Compatibility

- **Chrome**: 60+ (EventSource, ES6 modules, fetch)
- **Firefox**: 55+ (EventSource, ES6 modules, fetch)
- **Safari**: 12+ (EventSource, ES6 modules, fetch)
- **Edge**: 79+ (Chromium-based)

### Polyfills for Older Browsers

```html
<!-- EventSource polyfill for IE/older browsers -->
<script src="https://cdn.jsdelivr.net/npm/event-source-polyfill@1.0.25/src/eventsource.min.js"></script>

<!-- Fetch polyfill -->
<script src="https://cdn.jsdelivr.net/npm/whatwg-fetch@3.6.2/dist/fetch.umd.js"></script>
```

## 🚨 Error Codes

| Code | Description | Recoverable |
|------|-------------|-------------|
| `CONNECTION_FAILED` | Failed to establish connection | Yes |
| `AUTHENTICATION_FAILED` | Invalid API key | No |
| `TOOL_EXECUTION_FAILED` | MCP tool execution error | No |
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded | Yes |
| `INVALID_RESPONSE` | Invalid server response | No |
| `NETWORK_ERROR` | Network connectivity issue | Yes |
| `TIMEOUT` | Request or connection timeout | Yes |
| `PARSE_ERROR` | DSL parsing error | No |

## 📋 DSL Format Examples

### Simple Button
```json
{
  "type": "button",
  "text": "Click Me",
  "style": {
    "backgroundColor": "#007bff",
    "color": "white",
    "padding": "10px 20px",
    "border": "none",
    "borderRadius": "4px"
  }
}
```

### Login Form
```json
{
  "type": "form",
  "title": "Login",
  "fields": [
    {
      "type": "input",
      "name": "username",
      "label": "Username",
      "placeholder": "Enter your username"
    },
    {
      "type": "input",
      "name": "password",
      "label": "Password",
      "inputType": "password"
    },
    {
      "type": "button",
      "text": "Login",
      "style": { "backgroundColor": "#28a745" }
    }
  ]
}
```

## 🔐 Security Considerations

- Always use HTTPS in production
- Store API keys securely (environment variables, secure storage)
- Implement proper CORS configuration on the server
- Validate and sanitize DSL content before rendering
- Monitor rate limits and implement appropriate throttling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: [API Reference](API.md)
- **Examples**: Check the `demo-*.html` files
- **Issues**: Submit issues on GitHub
- **Discord**: Join our development community

## 🗺️ Roadmap

- [ ] WebSocket support as alternative to SSE
- [ ] React/Vue.js component wrappers
- [ ] Node.js server-side rendering support
- [ ] Advanced DSL validation with schema support
- [ ] Real-time collaborative editing
- [ ] Plugin system for custom DSL types