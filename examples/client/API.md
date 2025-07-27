# MCP SSE Client API Reference

Complete API reference for the MCP SSE Client library.

## Table of Contents

- [Classes](#classes)
  - [MCPSSEClient](#mcpsseclient)
  - [ProgressBar](#progressbar)
  - [EventLogger](#eventlogger)
  - [ConnectionStatus](#connectionstatus)
  - [ResultDisplay](#resultdisplay)
- [Types](#types)
- [Constants](#constants)
- [Utility Functions](#utility-functions)
- [Events](#events)
- [Error Handling](#error-handling)

## Classes

### MCPSSEClient

Main client class for connecting to the MCP server via Server-Sent Events.

#### Constructor

```typescript
new MCPSSEClient(baseUrl: string, apiKey?: string, config?: Partial<ClientConfig>)
```

**Parameters:**
- `baseUrl` (string): Base URL of the MCP server
- `apiKey` (string, optional): API key for authentication
- `config` (Partial<ClientConfig>, optional): Additional configuration options

**Example:**
```javascript
const client = new MCPSSEClient('http://localhost:8000', 'your-api-key', {
    debug: true,
    maxReconnectAttempts: 10,
    reconnectInterval: 2000
});
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `baseUrl` | `string` | Base URL of the MCP server (readonly) |
| `apiKey` | `string \| undefined` | API key for authentication (readonly) |
| `config` | `Required<ClientConfig>` | Client configuration (readonly) |
| `connectionState` | `ConnectionStateValue` | Current connection state (readonly) |
| `connectionId` | `string \| null` | Current connection ID (readonly) |
| `reconnectAttempts` | `number` | Number of reconnect attempts (readonly) |
| `debug` | `boolean` | Debug mode flag (readonly) |

#### Getters

| Getter | Type | Description |
|--------|------|-------------|
| `isConnected` | `boolean` | True if currently connected |
| `state` | `ConnectionStateValue` | Current connection state |
| `id` | `string \| null` | Connection ID or null if not connected |
| `activeRequestCount` | `number` | Number of active requests |
| `reconnectCount` | `number` | Number of reconnect attempts |

#### Methods

##### `connect(): Promise<void>`

Establishes SSE connection to the server.

**Returns:** Promise that resolves when connected

**Throws:** Error if connection fails

**Example:**
```javascript
try {
    await client.connect();
    console.log('Connected successfully');
} catch (error) {
    console.error('Connection failed:', error.message);
}
```

##### `disconnect(): void`

Closes the SSE connection and cleans up resources.

**Example:**
```javascript
client.disconnect();
```

##### `renderUIMarkup(request: RenderRequest, executionOptions?: ToolExecutionOptions): Promise<RenderResult>`

Renders DSL content to PNG with real-time progress updates.

**Parameters:**
- `request` (RenderRequest): Render request configuration
- `executionOptions` (ToolExecutionOptions, optional): Execution options

**Returns:** Promise resolving to render result

**Example:**
```javascript
const result = await client.renderUIMarkup({
    dsl_content: JSON.stringify({ type: 'button', text: 'Hello' }),
    options: { width: 800, height: 600 },
    async_mode: false
}, {
    timeout: 60000,
    progress_callback: (progress) => console.log(`${progress.progress}%`)
});
```

##### `validateDSL(request: ValidationRequest, executionOptions?: ToolExecutionOptions): Promise<ValidationResult>`

Validates DSL content without rendering.

**Parameters:**
- `request` (ValidationRequest): Validation request configuration
- `executionOptions` (ToolExecutionOptions, optional): Execution options

**Returns:** Promise resolving to validation result

**Example:**
```javascript
const result = await client.validateDSL({
    dsl_content: JSON.stringify({ type: 'button', text: 'Hello' }),
    options: { strict: true }
});

if (!result.valid) {
    console.log('Validation errors:', result.errors);
}
```

##### `getRenderStatus(request: StatusRequest, executionOptions?: ToolExecutionOptions): Promise<TaskStatusResult>`

Gets the status of an async rendering task.

**Parameters:**
- `request` (StatusRequest): Status request configuration
- `executionOptions` (ToolExecutionOptions, optional): Execution options

**Returns:** Promise resolving to task status

**Example:**
```javascript
const status = await client.getRenderStatus({
    task_id: 'task_12345',
    include_result: true
});

console.log('Task status:', status.status);
if (status.result) {
    console.log('Task completed with result:', status.result);
}
```

### ProgressBar

UI component for displaying rendering progress.

#### Constructor

```typescript
new ProgressBar(container: HTMLElement, options?: ProgressBarOptions)
```

**Parameters:**
- `container` (HTMLElement): Container element for the progress bar
- `options` (ProgressBarOptions, optional): Configuration options

**Example:**
```javascript
const progressBar = new ProgressBar(document.getElementById('progress'), {
    showPercentage: true,
    showMessage: true,
    showStage: true,
    animate: true
});
```

#### Methods

##### `update(progress: number, message?: string, stage?: string, timeRemaining?: number): void`

Updates the progress bar display.

**Parameters:**
- `progress` (number): Progress percentage (0-100)
- `message` (string, optional): Progress message
- `stage` (string, optional): Current processing stage
- `timeRemaining` (number, optional): Estimated time remaining in seconds

##### `reset(): void`

Resets the progress bar to initial state.

##### `setError(message: string): void`

Sets the progress bar to error state.

##### `setSuccess(message: string): void`

Sets the progress bar to success state.

##### `clearState(): void`

Clears error/success state classes.

### EventLogger

UI component for logging and displaying events.

#### Constructor

```typescript
new EventLogger(container: HTMLElement, options?: EventLoggerOptions)
```

#### Methods

##### `log(level: string, message: string, data?: any, eventType?: string): void`

Logs an event with specified level.

##### `info(message: string, data?: any, eventType?: string): void`

Logs an info-level message.

##### `warn(message: string, data?: any, eventType?: string): void`

Logs a warning-level message.

##### `error(message: string, data?: any, eventType?: string): void`

Logs an error-level message.

##### `clear(): void`

Clears all logged events.

##### `export(): string`

Exports all events as JSON string.

### ConnectionStatus

UI component for displaying connection status.

#### Constructor

```typescript
new ConnectionStatus(container: HTMLElement)
```

#### Methods

##### `update(state: string, connectionId?: string, reconnectCount?: number): void`

Updates the connection status display.

### ResultDisplay

UI component for displaying render results.

#### Constructor

```typescript
new ResultDisplay(container: HTMLElement)
```

#### Methods

##### `displayRenderResult(result: RenderResult): void`

Displays a render result with image and metadata.

##### `displayValidationResult(result: ValidationResult): void`

Displays a validation result with errors and suggestions.

##### `displayTaskStatus(result: TaskStatusResult): void`

Displays task status information.

##### `clear(): void`

Clears the result display.

## Types

### Core Types

#### `ClientConfig`

```typescript
interface ClientConfig {
  baseUrl: string;
  apiKey?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  reconnectExponentialBase?: number;
  heartbeatTimeout?: number;
  requestTimeout?: number;
  connectionTimeout?: number;
  debug?: boolean;
}
```

#### `RenderOptions`

```typescript
interface RenderOptions {
  width?: number;
  height?: number;
  device_scale_factor?: number;
  wait_for_load?: boolean;
  optimize_png?: boolean;
  transparent_background?: boolean;
}
```

#### `RenderRequest`

```typescript
interface RenderRequest {
  dsl_content: string;
  options?: RenderOptions;
  async_mode?: boolean;
}
```

#### `RenderResult`

```typescript
interface RenderResult {
  success: boolean;
  base64Data?: string;
  width?: number;
  height?: number;
  file_size?: number;
  metadata?: Record<string, any>;
  processing_time?: number;
  error?: string;
  task_id?: string;
}
```

#### `ValidationRequest`

```typescript
interface ValidationRequest {
  dsl_content: string;
  options?: ValidationOptions;
}
```

#### `ValidationResult`

```typescript
interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  suggestions: string[];
}
```

#### `StatusRequest`

```typescript
interface StatusRequest {
  task_id: string;
  include_result?: boolean;
}
```

#### `TaskStatusResult`

```typescript
interface TaskStatusResult {
  task_id: string;
  status: TaskStatusValue;
  progress?: number;
  message?: string;
  result?: RenderResult;
  created_at?: string;
  updated_at?: string;
}
```

#### `ToolExecutionOptions`

```typescript
interface ToolExecutionOptions {
  timeout?: number;
  progress_callback?: (progress: ProgressEventData) => void;
  request_id?: string;
}
```

### Event Data Types

#### `ProgressEventData`

```typescript
interface ProgressEventData {
  operation: string;
  progress: number; // 0-100
  message: string;
  stage?: string;
  estimated_remaining?: number;
  details?: Record<string, any>;
}
```

#### `ConnectionEventData`

```typescript
interface ConnectionEventData {
  message: string;
  connection_id: string;
  timestamp: string;
  metadata?: Record<string, any>;
}
```

#### `ErrorEventData`

```typescript
interface ErrorEventData {
  error_code: string;
  error_message: string;
  details?: Record<string, any>;
  recoverable: boolean;
  suggested_action?: string;
}
```

## Constants

### SSE Event Types

```typescript
const SSEEventType = {
  CONNECTION_OPENED: 'connection.opened',
  CONNECTION_HEARTBEAT: 'connection.heartbeat',
  CONNECTION_ERROR: 'connection.error',
  CONNECTION_CLOSED: 'connection.closed',
  MCP_TOOL_CALL: 'mcp.tool.call',
  MCP_TOOL_RESPONSE: 'mcp.tool.response',
  MCP_TOOL_ERROR: 'mcp.tool.error',
  MCP_TOOL_PROGRESS: 'mcp.tool.progress',
  RENDER_STARTED: 'render.started',
  RENDER_PROGRESS: 'render.progress',
  RENDER_COMPLETED: 'render.completed',
  RENDER_FAILED: 'render.failed',
  VALIDATION_STARTED: 'validation.started',
  VALIDATION_COMPLETED: 'validation.completed',
  VALIDATION_FAILED: 'validation.failed',
  STATUS_UPDATE: 'status.update',
  SERVER_ERROR: 'server.error',
  RATE_LIMIT_WARNING: 'rate_limit.warning',
  RATE_LIMIT_EXCEEDED: 'rate_limit.exceeded'
};
```

### Connection States

```typescript
const ConnectionState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  FAILED: 'failed'
};
```

### Task Status Values

```typescript
const TaskStatus = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
};
```

### Error Codes

```typescript
const ERROR_CODES = {
  CONNECTION_FAILED: 'CONNECTION_FAILED',
  AUTHENTICATION_FAILED: 'AUTHENTICATION_FAILED',
  TOOL_EXECUTION_FAILED: 'TOOL_EXECUTION_FAILED',
  RATE_LIMIT_EXCEEDED: 'RATE_LIMIT_EXCEEDED',
  INVALID_RESPONSE: 'INVALID_RESPONSE',
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',
  PARSE_ERROR: 'PARSE_ERROR'
};
```

## Utility Functions

### Type Validation

#### `isValidEventType(eventType: string): boolean`

Checks if a value is a valid SSE event type.

#### `isValidToolName(toolName: string): boolean`

Checks if a value is a valid MCP tool name.

#### `isValidConnectionState(state: string): boolean`

Checks if a value is a valid connection state.

### Data Validation

#### `validateRenderOptions(options?: RenderOptions): ValidationResult`

Validates render options and returns validation result.

#### `validateDSLContent(dslContent: string): ValidationResult`

Validates DSL content format and returns validation result.

### Configuration

#### `getDefaultRenderOptions(): Required<RenderOptions>`

Returns default render options.

#### `mergeWithDefaults(userOptions?: RenderOptions): Required<RenderOptions>`

Merges user options with defaults.

### ID Generation

#### `generateRequestId(): string`

Generates a unique request ID.

#### `generateConnectionId(): string`

Generates a unique connection ID.

### Formatting

#### `formatBytes(bytes: number): string`

Formats bytes to human-readable string (e.g., "1.2 MB").

#### `formatDuration(ms: number): string`

Formats duration in milliseconds to human-readable string (e.g., "1.2s").

### Demo Utilities

#### `setupClientLogging(client: MCPSSEClient, logger: EventLogger): void`

Sets up automatic event logging for a client instance.

#### `getSampleDSL(): Record<string, {name: string, content: string}>`

Returns sample DSL content for demos.

#### `validateAndFormatDSL(content: string): {valid: boolean, formatted?: string, error?: string}`

Validates and formats DSL content.

## Events

The `MCPSSEClient` extends `EventTarget` and emits the following events:

### Connection Events

#### `connectionOpened`

Fired when SSE connection is established.

```typescript
client.addEventListener('connectionOpened', (event: ConnectionOpenedEvent) => {
  console.log('Connected:', event.detail.connection_id);
});
```

#### `connectionClosed`

Fired when SSE connection is closed.

```typescript
client.addEventListener('connectionClosed', (event: ConnectionClosedEvent) => {
  console.log('Disconnected:', event.detail.reason);
});
```

#### `connectionStateChanged`

Fired when connection state changes.

```typescript
client.addEventListener('connectionStateChanged', (event: ConnectionStateChangedEvent) => {
  console.log(`State: ${event.detail.oldState} → ${event.detail.newState}`);
});
```

### Progress Events

#### `renderProgress`

Fired during rendering with progress updates.

```typescript
client.addEventListener('renderProgress', (event: RenderProgressEvent) => {
  const { progress, message, stage } = event.detail;
  updateProgressBar(progress, message, stage);
});
```

### Completion Events

#### `renderCompleted`

Fired when rendering completes successfully.

```typescript
client.addEventListener('renderCompleted', (event: RenderCompletedEvent) => {
  displayResult(event.detail.result);
});
```

#### `renderFailed`

Fired when rendering fails.

```typescript
client.addEventListener('renderFailed', (event: RenderFailedEvent) => {
  showError(event.detail.error);
});
```

#### `validationCompleted`

Fired when DSL validation completes.

```typescript
client.addEventListener('validationCompleted', (event: ValidationCompletedEvent) => {
  displayValidationResult(event.detail);
});
```

### System Events

#### `error`

Fired when client errors occur.

```typescript
client.addEventListener('error', (event: ErrorEvent) => {
  const { code, message, details } = event.detail;
  handleError(code, message, details);
});
```

#### `heartbeat`

Fired when heartbeat is received from server.

```typescript
client.addEventListener('heartbeat', (event: HeartbeatEvent) => {
  updateLastHeartbeat(event.detail.timestamp);
});
```

#### `rateLimitWarning`

Fired when approaching rate limits.

```typescript
client.addEventListener('rateLimitWarning', (event: RateLimitWarningEvent) => {
  showRateLimitWarning(event.detail);
});
```

#### `rateLimitExceeded`

Fired when rate limits are exceeded.

```typescript
client.addEventListener('rateLimitExceeded', (event: RateLimitExceededEvent) => {
  handleRateLimitExceeded(event.detail);
});
```

## Error Handling

### Error Types

All client errors extend the base `MCPError` interface:

```typescript
interface MCPError extends Error {
  code: string;
  details?: Record<string, any>;
  recoverable?: boolean;
}
```

### Specific Error Types

#### `ConnectionError`

Errors related to connection establishment or maintenance.

#### `ToolExecutionError`

Errors during MCP tool execution.

#### `ValidationError`

Errors during DSL validation or parsing.

### Error Recovery

```typescript
client.addEventListener('error', (event) => {
  const { code, message, details } = event.detail;
  
  switch (code) {
    case ERROR_CODES.CONNECTION_FAILED:
      // Connection will auto-retry
      showConnectionRetryMessage();
      break;
      
    case ERROR_CODES.AUTHENTICATION_FAILED:
      // Non-recoverable, need new API key
      promptForApiKey();
      break;
      
    case ERROR_CODES.RATE_LIMIT_EXCEEDED:
      // Recoverable, wait for reset
      const resetTime = new Date(details.reset_time);
      showRateLimitMessage(resetTime);
      break;
      
    case ERROR_CODES.TIMEOUT:
      // Recoverable, retry request
      retryLastRequest();
      break;
      
    default:
      showGenericError(message);
  }
});
```

### Best Practices

1. **Always handle errors**: Set up error event listeners
2. **Check error codes**: Use specific error codes for different handling
3. **Respect rate limits**: Handle rate limiting gracefully
4. **Implement retries**: For recoverable errors, implement appropriate retry logic
5. **User feedback**: Provide clear feedback to users about error states
6. **Logging**: Log errors for debugging and monitoring

### Debugging

Enable debug mode for detailed logging:

```javascript
const client = new MCPSSEClient(baseUrl, apiKey, { debug: true });
```

Monitor client state:

```javascript
setInterval(() => {
  console.log({
    state: client.state,
    connected: client.isConnected,
    activeRequests: client.activeRequestCount,
    reconnectAttempts: client.reconnectCount
  });
}, 5000);
```

## Migration Guide

### From Version 0.x to 1.x

If migrating from an earlier version:

1. **Event names changed**: Use new event naming convention
2. **Type safety**: Import TypeScript types for better development experience
3. **Configuration**: Use new configuration object structure
4. **Error handling**: Update error handling for new error codes

### Browser Support

- **Modern browsers**: Use ES6 modules directly
- **Legacy browsers**: Add polyfills for EventSource, fetch, and Promise
- **Node.js**: Library works in Node.js with appropriate polyfills

## Performance Considerations

1. **Connection pooling**: Reuse client instances when possible
2. **Event listener cleanup**: Remove event listeners when components unmount
3. **Memory management**: Call `disconnect()` when finished
4. **Batch operations**: Use concurrent requests for multiple renders
5. **Progress callbacks**: Avoid heavy operations in progress callbacks

## Security Notes

1. **API key storage**: Store API keys securely, never in client-side code
2. **HTTPS**: Always use HTTPS in production
3. **Content validation**: Validate DSL content before sending
4. **Rate limiting**: Respect server rate limits
5. **CORS**: Ensure proper CORS configuration on server