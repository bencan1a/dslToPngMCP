/**
 * Demo Utilities
 * ==============
 * 
 * Utility functions and components for MCP SSE Client demo applications.
 * Provides UI components for progress tracking, event logging, and result display.
 */

import { formatBytes, formatDuration, SSEEventType } from '../lib/types.js';

/**
 * Progress Bar Component
 */
export class ProgressBar {
    /**
     * Create a progress bar component
     * @param {HTMLElement} container - Container element
     * @param {Object} options - Progress bar options
     */
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            showPercentage: true,
            showMessage: true,
            showStage: true,
            showTimeRemaining: true,
            animate: true,
            ...options
        };

        this.progress = 0;
        this.message = '';
        this.stage = '';
        this.timeRemaining = null;

        this._render();
    }

    /**
     * Update progress
     * @param {number} progress - Progress percentage (0-100)
     * @param {string} [message] - Progress message
     * @param {string} [stage] - Current stage
     * @param {number} [timeRemaining] - Estimated time remaining in seconds
     */
    update(progress, message, stage, timeRemaining) {
        this.progress = Math.max(0, Math.min(100, progress));
        if (message !== undefined) this.message = message;
        if (stage !== undefined) this.stage = stage;
        if (timeRemaining !== undefined) this.timeRemaining = timeRemaining;

        this._updateDisplay();
    }

    /**
     * Reset progress bar
     */
    reset() {
        this.progress = 0;
        this.message = '';
        this.stage = '';
        this.timeRemaining = null;
        this._updateDisplay();
    }

    /**
     * Set error state
     * @param {string} message - Error message
     */
    setError(message) {
        this.container.classList.add('error');
        this.message = message;
        this._updateDisplay();
    }

    /**
     * Set success state
     * @param {string} message - Success message
     */
    setSuccess(message) {
        this.container.classList.add('success');
        this.progress = 100;
        this.message = message;
        this._updateDisplay();
    }

    /**
     * Clear state classes
     */
    clearState() {
        this.container.classList.remove('error', 'success');
    }

    /**
     * Render initial progress bar structure
     * @private
     */
    _render() {
        this.container.innerHTML = `
      <div class="progress-wrapper">
        <div class="progress-bar">
          <div class="progress-fill"></div>
          <div class="progress-text"></div>
        </div>
        <div class="progress-info">
          <div class="progress-message"></div>
          <div class="progress-details">
            <span class="progress-stage"></span>
            <span class="progress-time-remaining"></span>
          </div>
        </div>
      </div>
    `;

        this.fillElement = this.container.querySelector('.progress-fill');
        this.textElement = this.container.querySelector('.progress-text');
        this.messageElement = this.container.querySelector('.progress-message');
        this.stageElement = this.container.querySelector('.progress-stage');
        this.timeRemainingElement = this.container.querySelector('.progress-time-remaining');
    }

    /**
     * Update display elements
     * @private
     */
    _updateDisplay() {
        // Update progress bar fill
        this.fillElement.style.width = `${this.progress}%`;

        // Update percentage text
        if (this.options.showPercentage) {
            this.textElement.textContent = `${Math.round(this.progress)}%`;
        }

        // Update message
        if (this.options.showMessage && this.message) {
            this.messageElement.textContent = this.message;
            this.messageElement.style.display = 'block';
        } else {
            this.messageElement.style.display = 'none';
        }

        // Update stage
        if (this.options.showStage && this.stage) {
            this.stageElement.textContent = `Stage: ${this.stage}`;
            this.stageElement.style.display = 'inline';
        } else {
            this.stageElement.style.display = 'none';
        }

        // Update time remaining
        if (this.options.showTimeRemaining && this.timeRemaining !== null) {
            this.timeRemainingElement.textContent = `ETA: ${formatDuration(this.timeRemaining * 1000)}`;
            this.timeRemainingElement.style.display = 'inline';
        } else {
            this.timeRemainingElement.style.display = 'none';
        }

        // Add animation class if enabled
        if (this.options.animate) {
            this.fillElement.style.transition = 'width 0.3s ease-in-out';
        }
    }
}

/**
 * Event Logger Component
 */
export class EventLogger {
    /**
     * Create an event logger component
     * @param {HTMLElement} container - Container element
     * @param {Object} options - Logger options
     */
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            maxEvents: 100,
            showTimestamps: true,
            showEventTypes: true,
            autoScroll: true,
            filterLevels: ['info', 'warn', 'error'],
            ...options
        };

        this.events = [];
        this._render();
    }

    /**
     * Log an event
     * @param {string} level - Log level (info, warn, error)
     * @param {string} message - Log message
     * @param {Object} [data] - Additional data
     * @param {string} [eventType] - SSE event type
     */
    log(level, message, data, eventType) {
        if (!this.options.filterLevels.includes(level)) {
            return;
        }

        const event = {
            id: Date.now() + Math.random(),
            timestamp: new Date(),
            level,
            message,
            data,
            eventType
        };

        this.events.unshift(event);

        // Limit number of events
        if (this.events.length > this.options.maxEvents) {
            this.events = this.events.slice(0, this.options.maxEvents);
        }

        this._renderEvents();
    }

    /**
     * Log info message
     * @param {string} message - Message
     * @param {Object} [data] - Additional data
     * @param {string} [eventType] - Event type
     */
    info(message, data, eventType) {
        this.log('info', message, data, eventType);
    }

    /**
     * Log warning message
     * @param {string} message - Message
     * @param {Object} [data] - Additional data
     * @param {string} [eventType] - Event type
     */
    warn(message, data, eventType) {
        this.log('warn', message, data, eventType);
    }

    /**
     * Log error message
     * @param {string} message - Message
     * @param {Object} [data] - Additional data
     * @param {string} [eventType] - Event type
     */
    error(message, data, eventType) {
        this.log('error', message, data, eventType);
    }

    /**
     * Clear all events
     */
    clear() {
        this.events = [];
        this._renderEvents();
    }

    /**
     * Export events as JSON
     * @returns {string} JSON string of events
     */
    export() {
        return JSON.stringify(this.events, null, 2);
    }

    /**
     * Render initial logger structure
     * @private
     */
    _render() {
        this.container.innerHTML = `
      <div class="event-logger">
        <div class="logger-header">
          <span class="logger-title">Event Log</span>
          <div class="logger-controls">
            <button class="clear-btn" type="button">Clear</button>
            <button class="export-btn" type="button">Export</button>
          </div>
        </div>
        <div class="logger-events"></div>
      </div>
    `;

        this.eventsContainer = this.container.querySelector('.logger-events');

        // Set up event listeners
        this.container.querySelector('.clear-btn').addEventListener('click', () => this.clear());
        this.container.querySelector('.export-btn').addEventListener('click', () => this._exportEvents());
    }

    /**
     * Render events list
     * @private
     */
    _renderEvents() {
        this.eventsContainer.innerHTML = this.events.map(event => `
      <div class="log-event ${event.level}" data-level="${event.level}">
        <div class="event-header">
          ${this.options.showTimestamps ? `<span class="event-timestamp">${event.timestamp.toLocaleTimeString()}</span>` : ''}
          <span class="event-level">${event.level.toUpperCase()}</span>
          ${this.options.showEventTypes && event.eventType ? `<span class="event-type">${event.eventType}</span>` : ''}
        </div>
        <div class="event-message">${this._escapeHtml(event.message)}</div>
        ${event.data ? `<div class="event-data"><pre>${this._escapeHtml(JSON.stringify(event.data, null, 2))}</pre></div>` : ''}
      </div>
    `).join('');

        // Auto scroll to top if enabled
        if (this.options.autoScroll) {
            this.eventsContainer.scrollTop = 0;
        }
    }

    /**
     * Export events to downloadable file
     * @private
     */
    _exportEvents() {
        const dataStr = this.export();
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);

        const link = document.createElement('a');
        link.href = url;
        link.download = `mcp-events-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    /**
     * Escape HTML characters
     * @private
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

/**
 * Connection Status Component
 */
export class ConnectionStatus {
    /**
     * Create a connection status component
     * @param {HTMLElement} container - Container element
     */
    constructor(container) {
        this.container = container;
        this.state = 'disconnected';
        this.connectionId = null;
        this.reconnectCount = 0;

        this._render();
    }

    /**
     * Update connection status
     * @param {string} state - Connection state
     * @param {string} [connectionId] - Connection ID
     * @param {number} [reconnectCount] - Reconnect attempts
     */
    update(state, connectionId, reconnectCount) {
        this.state = state;
        if (connectionId !== undefined) this.connectionId = connectionId;
        if (reconnectCount !== undefined) this.reconnectCount = reconnectCount;

        this._updateDisplay();
    }

    /**
     * Render initial status structure
     * @private
     */
    _render() {
        this.container.innerHTML = `
      <div class="connection-status">
        <div class="status-indicator"></div>
        <div class="status-text">
          <div class="status-state"></div>
          <div class="status-details"></div>
        </div>
      </div>
    `;

        this.indicatorElement = this.container.querySelector('.status-indicator');
        this.stateElement = this.container.querySelector('.status-state');
        this.detailsElement = this.container.querySelector('.status-details');

        this._updateDisplay();
    }

    /**
     * Update display elements
     * @private
     */
    _updateDisplay() {
        // Update indicator and state text
        this.container.className = `connection-status ${this.state}`;
        this.indicatorElement.className = `status-indicator ${this.state}`;

        const stateText = {
            'disconnected': 'Disconnected',
            'connecting': 'Connecting...',
            'connected': 'Connected',
            'reconnecting': 'Reconnecting...',
            'failed': 'Connection Failed'
        };

        this.stateElement.textContent = stateText[this.state] || this.state;

        // Update details
        let details = '';
        if (this.state === 'connected' && this.connectionId) {
            details = `ID: ${this.connectionId.substring(0, 8)}...`;
        } else if (this.state === 'reconnecting' && this.reconnectCount > 0) {
            details = `Attempt ${this.reconnectCount}`;
        } else if (this.state === 'failed' && this.reconnectCount > 0) {
            details = `Failed after ${this.reconnectCount} attempts`;
        }

        this.detailsElement.textContent = details;
    }
}

/**
 * Result Display Component
 */
export class ResultDisplay {
    /**
     * Create a result display component
     * @param {HTMLElement} container - Container element
     */
    constructor(container) {
        this.container = container;
        this._render();
    }

    /**
     * Display render result
     * @param {Object} result - Render result
     */
    displayRenderResult(result) {
        if (!result.success) {
            this._displayError(result.error || 'Rendering failed');
            return;
        }

        const content = `
      <div class="result-success">
        <h3>Render Completed</h3>
        <div class="result-image">
          <img src="data:image/png;base64,${result.base64Data}" alt="Rendered DSL" />
        </div>
        <div class="result-metadata">
          <div class="metadata-item">
            <label>Dimensions:</label>
            <span>${result.width} × ${result.height} px</span>
          </div>
          <div class="metadata-item">
            <label>File Size:</label>
            <span>${formatBytes(result.file_size)}</span>
          </div>
          <div class="metadata-item">
            <label>Processing Time:</label>
            <span>${formatDuration(result.processing_time * 1000)}</span>
          </div>
          ${result.task_id ? `
            <div class="metadata-item">
              <label>Task ID:</label>
              <span>${result.task_id}</span>
            </div>
          ` : ''}
        </div>
        <div class="result-actions">
          <button class="download-btn" type="button">Download PNG</button>
          <button class="copy-btn" type="button">Copy Base64</button>
        </div>
      </div>
    `;

        this.container.innerHTML = content;

        // Set up event listeners
        this.container.querySelector('.download-btn').addEventListener('click', () => {
            this._downloadImage(result.base64Data, 'rendered-dsl.png');
        });

        this.container.querySelector('.copy-btn').addEventListener('click', () => {
            this._copyToClipboard(result.base64Data);
        });
    }

    /**
     * Display validation result
     * @param {Object} result - Validation result
     */
    displayValidationResult(result) {
        const statusClass = result.valid ? 'success' : 'error';
        const statusText = result.valid ? 'Valid' : 'Invalid';

        const content = `
      <div class="result-${statusClass}">
        <h3>Validation ${statusText}</h3>
        ${result.errors.length > 0 ? `
          <div class="validation-errors">
            <h4>Errors:</h4>
            <ul>
              ${result.errors.map(error => `<li>${this._escapeHtml(error)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
        ${result.warnings.length > 0 ? `
          <div class="validation-warnings">
            <h4>Warnings:</h4>
            <ul>
              ${result.warnings.map(warning => `<li>${this._escapeHtml(warning)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
        ${result.suggestions.length > 0 ? `
          <div class="validation-suggestions">
            <h4>Suggestions:</h4>
            <ul>
              ${result.suggestions.map(suggestion => `<li>${this._escapeHtml(suggestion)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
      </div>
    `;

        this.container.innerHTML = content;
    }

    /**
     * Display task status result
     * @param {Object} result - Task status result
     */
    displayTaskStatus(result) {
        const content = `
      <div class="result-info">
        <h3>Task Status</h3>
        <div class="status-metadata">
          <div class="metadata-item">
            <label>Task ID:</label>
            <span>${result.task_id}</span>
          </div>
          <div class="metadata-item">
            <label>Status:</label>
            <span class="status-badge ${result.status}">${result.status.toUpperCase()}</span>
          </div>
          ${result.progress !== undefined ? `
            <div class="metadata-item">
              <label>Progress:</label>
              <span>${result.progress}%</span>
            </div>
          ` : ''}
          ${result.message ? `
            <div class="metadata-item">
              <label>Message:</label>
              <span>${this._escapeHtml(result.message)}</span>
            </div>
          ` : ''}
          ${result.created_at ? `
            <div class="metadata-item">
              <label>Created:</label>
              <span>${new Date(result.created_at).toLocaleString()}</span>
            </div>
          ` : ''}
          ${result.updated_at ? `
            <div class="metadata-item">
              <label>Updated:</label>
              <span>${new Date(result.updated_at).toLocaleString()}</span>
            </div>
          ` : ''}
        </div>
        ${result.result ? `
          <div class="task-result">
            <h4>Result:</h4>
            <pre>${this._escapeHtml(JSON.stringify(result.result, null, 2))}</pre>
          </div>
        ` : ''}
      </div>
    `;

        this.container.innerHTML = content;
    }

    /**
     * Display error message
     * @param {string} message - Error message
     */
    _displayError(message) {
        this.container.innerHTML = `
      <div class="result-error">
        <h3>Error</h3>
        <p>${this._escapeHtml(message)}</p>
      </div>
    `;
    }

    /**
     * Clear result display
     */
    clear() {
        this.container.innerHTML = '<div class="result-empty">No results yet</div>';
    }

    /**
     * Render initial structure
     * @private
     */
    _render() {
        this.clear();
    }

    /**
     * Download image from base64 data
     * @private
     * @param {string} base64Data - Base64 encoded image data
     * @param {string} filename - Filename for download
     */
    _downloadImage(base64Data, filename) {
        const link = document.createElement('a');
        link.href = `data:image/png;base64,${base64Data}`;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    /**
     * Copy text to clipboard
     * @private
     * @param {string} text - Text to copy
     */
    async _copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            // Could show a toast notification here
            console.log('Copied to clipboard');
        } catch (err) {
            console.error('Failed to copy to clipboard:', err);
        }
    }

    /**
     * Escape HTML characters
     * @private
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

/**
 * Demo Helper Functions
 */

/**
 * Create a basic MCPSSEClient event logger setup
 * @param {MCPSSEClient} client - MCP SSE Client instance
 * @param {EventLogger} logger - Event logger instance
 */
export function setupClientLogging(client, logger) {
    // Connection events
    client.addEventListener('connectionOpened', (event) => {
        logger.info('Connection opened', event.detail, SSEEventType.CONNECTION_OPENED);
    });

    client.addEventListener('connectionClosed', (event) => {
        logger.warn('Connection closed', event.detail, SSEEventType.CONNECTION_CLOSED);
    });

    client.addEventListener('connectionStateChanged', (event) => {
        logger.info(`Connection state: ${event.detail.oldState} → ${event.detail.newState}`, event.detail);
    });

    client.addEventListener('error', (event) => {
        logger.error('Client error', event.detail);
    });

    // Progress events
    client.addEventListener('renderProgress', (event) => {
        logger.info(`Progress: ${event.detail.progress}% - ${event.detail.message}`, event.detail, SSEEventType.RENDER_PROGRESS);
    });

    // Completion events
    client.addEventListener('renderCompleted', (event) => {
        logger.info('Render completed', event.detail, SSEEventType.RENDER_COMPLETED);
    });

    client.addEventListener('renderFailed', (event) => {
        logger.error('Render failed', event.detail, SSEEventType.RENDER_FAILED);
    });

    client.addEventListener('validationCompleted', (event) => {
        logger.info(`Validation completed: ${event.detail.valid ? 'Valid' : 'Invalid'}`, event.detail, SSEEventType.VALIDATION_COMPLETED);
    });

    // Rate limiting events
    client.addEventListener('rateLimitWarning', (event) => {
        logger.warn('Rate limit warning', event.detail, SSEEventType.RATE_LIMIT_WARNING);
    });

    client.addEventListener('rateLimitExceeded', (event) => {
        logger.error('Rate limit exceeded', event.detail, SSEEventType.RATE_LIMIT_EXCEEDED);
    });

    // Heartbeat events
    client.addEventListener('heartbeat', (event) => {
        logger.info('Heartbeat received', event.detail, SSEEventType.CONNECTION_HEARTBEAT);
    });
}

/**
 * Get sample DSL content for demos
 * @returns {Object} Sample DSL objects
 */
export function getSampleDSL() {
    return {
        simple: {
            name: 'Simple Button',
            content: JSON.stringify({
                type: 'button',
                text: 'Click Me',
                style: {
                    backgroundColor: '#007bff',
                    color: 'white',
                    padding: '10px 20px',
                    border: 'none',
                    borderRadius: '4px',
                    fontSize: '16px'
                }
            }, null, 2)
        },
        form: {
            name: 'Login Form',
            content: JSON.stringify({
                type: 'form',
                title: 'Login',
                fields: [
                    {
                        type: 'input',
                        name: 'username',
                        label: 'Username',
                        placeholder: 'Enter your username'
                    },
                    {
                        type: 'input',
                        name: 'password',
                        label: 'Password',
                        inputType: 'password',
                        placeholder: 'Enter your password'
                    },
                    {
                        type: 'button',
                        text: 'Login',
                        style: {
                            backgroundColor: '#28a745',
                            color: 'white'
                        }
                    }
                ]
            }, null, 2)
        },
        dashboard: {
            name: 'Dashboard Card',
            content: JSON.stringify({
                type: 'card',
                title: 'Sales Dashboard',
                content: [
                    {
                        type: 'metric',
                        label: 'Total Sales',
                        value: '$12,345',
                        trend: 'up',
                        change: '+15%'
                    },
                    {
                        type: 'chart',
                        chartType: 'line',
                        data: [10, 15, 12, 18, 22, 19, 25]
                    }
                ]
            }, null, 2)
        }
    };
}

/**
 * Validate and format DSL content
 * @param {string} content - DSL content to validate
 * @returns {Object} Validation result
 */
export function validateAndFormatDSL(content) {
    try {
        const parsed = JSON.parse(content);
        const formatted = JSON.stringify(parsed, null, 2);
        return {
            valid: true,
            formatted,
            parsed
        };
    } catch (error) {
        return {
            valid: false,
            error: error.message,
            formatted: content
        };
    }
}