class FlowDesigner {
    constructor() {
        this.nodes = new Map();
        this.connections = [];
        this.selectedNode = null;
        this.nodeCounter = 0;
        this.draggedElement = null;
        this.canvas = document.getElementById('designCanvas');
        this.connectionSvg = document.getElementById('connectionSvg');

        // Node and connector constants (matching CSS)
        this.NODE_WIDTH = 100;
        this.NODE_HEIGHT = 50;
        this.CONNECTOR_SIZE = 16;
        this.CONNECTOR_OFFSET = 8;

        this.config = {
            minTemp: -40,
            maxTemp: 100,
            maxHoldTime: 1440
        };

        this.init();
        this.loadConfig();
    }

    init() {
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.updateStatus();
    }

    async loadConfig() {
        try {
            const response = await fetch('/get-flow-config');
            const data = await response.json();
            this.config = { ...this.config, ...data };
        } catch (error) {
            console.error('Failed to load config:', error);
        }
    }

    setupEventListeners() {
        // Header controls
        document.getElementById('clearCanvas').addEventListener('click', () => this.clearCanvas());
        document.getElementById('validateFlow').addEventListener('click', () => this.validateFlow());
        document.getElementById('exportFlow').addEventListener('click', () => this.exportFlow());

        // Canvas events
        this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));

        // Window resize
        window.addEventListener('resize', () => this.redrawConnections());
    }

    setupDragAndDrop() {
        // Make node templates draggable
        document.querySelectorAll('.node-template').forEach(template => {
            template.draggable = true;
            template.addEventListener('dragstart', (e) => this.handleDragStart(e));
        });

        // Setup canvas drop zone
        this.canvas.addEventListener('dragover', (e) => e.preventDefault());
        this.canvas.addEventListener('drop', (e) => this.handleDrop(e));
    }

    handleDragStart(e) {
        this.draggedElement = e.target.closest('.node-template');
        e.dataTransfer.effectAllowed = 'copy';
    }

    handleDrop(e) {
        e.preventDefault();
        if (!this.draggedElement) return;

        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const nodeType = this.draggedElement.dataset.nodeType;
        this.createNode(nodeType, x, y);
        this.draggedElement = null;
    }

    createNode(type, x, y) {
        const nodeId = `node_${++this.nodeCounter}`;
        const nodeElement = this.createNodeElement(type, nodeId, x, y);

        const nodeData = {
            id: nodeId,
            type: type,
            x: x,
            y: y,
            element: nodeElement,
            properties: this.getDefaultProperties(type)
        };

        this.nodes.set(nodeId, nodeData);
        this.canvas.appendChild(nodeElement);
        this.updateStatus();

        return nodeData;
    }

    createNodeElement(type, id, x, y) {
        const node = document.createElement('div');
        node.className = 'flow-node';
        node.dataset.nodeId = id;
        node.dataset.nodeType = type;
        node.style.left = `${x - 50}px`;
        node.style.top = `${y - 25}px`;

        const config = this.getNodeConfig(type);

        // Determine which connectors this node should have
        let connectorsHtml = '';
        if (type === 'start-node') {
            // Start nodes only have output connector
            connectorsHtml = '<div class="node-connector start" data-connection-type="start"></div>';
        } else if (type === 'end-node') {
            // End nodes only have input connector
            connectorsHtml = '<div class="node-connector end" data-connection-type="end"></div>';
        } else {
            // Other nodes have both connectors
            connectorsHtml = `
                <div class="node-connector start" data-connection-type="start"></div>
                <div class="node-connector end" data-connection-type="end"></div>
            `;
        }

        node.innerHTML = `
            <div class="node-icon">${config.icon}</div>
            <div class="node-label">${config.label}</div>
            ${connectorsHtml}
            <div class="node-delete" onclick="flowDesigner.deleteNode('${id}')">&times;</div>
        `;

        // Make node selectable and draggable
        node.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectNode(id);
        });

        this.makeNodeDraggable(node);
        this.setupNodeConnectors(node);

        return node;
    }

    getNodeConfig(type) {
        const configs = {
            'start-node': { icon: '🚀', label: 'Start' },
            'temperature-goal': { icon: '🎯', label: 'Temp Goal' },
            'temperature-hold': { icon: '⏱️', label: 'Temp Hold' },
            'end-node': { icon: '🏁', label: 'End' }
        };
        return configs[type] || { icon: '❓', label: 'Unknown' };
    }

    getDefaultProperties(type) {
        const defaults = {
            'start-node': { initialTemperature: 20, readCurrent: false },
            'temperature-goal': { temperature: 20, tolerance: 0.5 },
            'temperature-hold': { duration: 30, tolerance: 0.5 }, // No temperature property
            'end-node': { cooldown: false }
        };
        return defaults[type] || {};
    }

    makeNodeDraggable(node) {
        let isDragging = false;
        let dragOffset = { x: 0, y: 0 };
        let hasMovedDuringDrag = false;

        node.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('node-delete') ||
                e.target.classList.contains('node-connector')) return;

            isDragging = true;
            hasMovedDuringDrag = false;
            const rect = node.getBoundingClientRect();
            dragOffset.x = e.clientX - rect.left;
            dragOffset.y = e.clientY - rect.top;

            node.style.zIndex = '1000';
            // Don't prevent default here to allow click events to work
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            hasMovedDuringDrag = true;
            const canvasRect = this.canvas.getBoundingClientRect();
            const x = e.clientX - canvasRect.left - dragOffset.x;
            const y = e.clientY - canvasRect.top - dragOffset.y;

            node.style.left = `${Math.max(0, Math.min(x, this.canvas.clientWidth - 100))}px`;
            node.style.top = `${Math.max(0, Math.min(y, this.canvas.clientHeight - 50))}px`;

            // Update node data (stored positions match style.left/top for consistency)
            const nodeData = this.nodes.get(node.dataset.nodeId);
            if (nodeData) {
                nodeData.x = parseInt(node.style.left) || 0; // Left edge position
                nodeData.y = parseInt(node.style.top) || 0;  // Top edge position
            }

            // Redraw connections immediately for accurate positioning
            this.redrawConnections();
        });

        document.addEventListener('mouseup', (e) => {
            if (isDragging) {
                isDragging = false;
                node.style.zIndex = '';

                // Final redraw to ensure accuracy
                this.redrawConnections();

                // If the user didn't move the mouse much, treat it as a click for selection
                if (!hasMovedDuringDrag) {
                    // Trigger selection after a small delay to ensure the click event can fire
                    setTimeout(() => {
                        this.selectNode(node.dataset.nodeId);
                    }, 10);
                }
            }
        });
    }

    setupNodeConnectors(node) {
        const connectors = node.querySelectorAll('.node-connector');
        connectors.forEach(connector => {
            this.setupConnectorEvents(connector, node.dataset.nodeId);
        });
    }

    setupConnectorEvents(connector, nodeId) {
        // Only start connections can initiate connections
        connector.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();

            if (connector.dataset.connectionType === 'start') {
                if (this.pendingConnection) {
                    // Cancel current connection
                    this.clearPendingConnection();
                } else {
                    // Start new connection
                    this.startConnection(connector, nodeId);
                }
            } else if (connector.dataset.connectionType === 'end' && this.pendingConnection) {
                // Complete connection
                this.completeConnection(nodeId);
            }
        });

        // Visual feedback when hovering over valid targets
        connector.addEventListener('mouseenter', (e) => {
            if (this.pendingConnection && connector.dataset.connectionType === 'end') {
                connector.classList.add('connection-target');
                this.showPreviewLine(nodeId);
            } else if (!this.pendingConnection && connector.dataset.connectionType === 'start') {
                connector.classList.add('can-start');
            }
        });

        connector.addEventListener('mouseleave', (e) => {
            connector.classList.remove('connection-target', 'can-start');
            this.hidePreviewLine();
        });
    }

    startConnection(connector, nodeId) {
        console.log('Starting connection from:', nodeId);

        this.pendingConnection = {
            nodeId: nodeId,
            type: 'start',
            connector: connector
        };

        connector.classList.add('pending');
    }

    showPreviewLine(toNodeId) {
        if (!this.pendingConnection) return;

        this.hidePreviewLine(); // Clear any existing preview

        const fromNode = this.nodes.get(this.pendingConnection.nodeId);
        const toNode = this.nodes.get(toNodeId);

        if (!fromNode || !toNode) return;

        // Calculate precise connector positions
        const fromPos = this.getConnectorPosition(fromNode, 'start');
        const toPos = this.getConnectorPosition(toNode, 'end');

        console.log('PREVIEW: From node', this.pendingConnection.nodeId, 'at', fromPos);
        console.log('PREVIEW: To node', toNodeId, 'at', toPos);

        // Validate coordinates
        if (fromPos.x === 0 && fromPos.y === 0 || toPos.x === 0 && toPos.y === 0) {
            console.error('Invalid connector positions detected');
            return;
        }

        this.previewLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        this.previewLine.setAttribute('x1', fromPos.x);
        this.previewLine.setAttribute('y1', fromPos.y);
        this.previewLine.setAttribute('x2', toPos.x);
        this.previewLine.setAttribute('y2', toPos.y);
        this.previewLine.setAttribute('stroke', '#ffc107');
        this.previewLine.setAttribute('stroke-width', '3');
        this.previewLine.setAttribute('stroke-dasharray', '5,5');
        this.previewLine.style.pointerEvents = 'none';
        this.previewLine.classList.add('preview-line');

        this.connectionSvg.appendChild(this.previewLine);
    }

    hidePreviewLine() {
        if (this.previewLine) {
            this.previewLine.remove();
            this.previewLine = null;
        }
    }

    getConnectorPosition(node, type) {
        // Use the node's exact position in the canvas coordinate system
        // Node position is stored as the top-left corner when created/dragged
        const nodeLeft = parseInt(node.element.style.left) || 0;
        const nodeTop = parseInt(node.element.style.top) || 0;

        let x, y;

        if (type === 'start') {
            // Start connector: positioned at right edge, vertically centered
            // CSS: right: -8px, top: 50%, so connector center is at:
            x = nodeLeft + this.NODE_WIDTH + this.CONNECTOR_OFFSET; // Right edge + offset
            y = nodeTop + (this.NODE_HEIGHT / 2); // Vertical center
        } else if (type === 'end') {
            // End connector: positioned at left edge, vertically centered
            // CSS: left: -8px, top: 50%, so connector center is at:
            x = nodeLeft - this.CONNECTOR_OFFSET; // Left edge - offset
            y = nodeTop + (this.NODE_HEIGHT / 2); // Vertical center
        } else {
            console.error('Unknown connector type:', type);
            return { x: 0, y: 0 };
        }

        console.log(`${type} connector for node ${node.id}:`, { x, y }, 'Node at:', { nodeLeft, nodeTop });

        return { x, y };
    }

    completeConnection(toNodeId) {
        if (!this.pendingConnection) return;

        const fromNodeId = this.pendingConnection.nodeId;

        if (fromNodeId !== toNodeId) {
            this.createConnection(fromNodeId, toNodeId);
            console.log('Connection completed:', fromNodeId, '->', toNodeId);
        }

        this.clearPendingConnection();
    }


    handleConnectorClick(nodeId, connector) {
        console.log('Connector clicked:', nodeId, connector.dataset.connectionType);

        if (this.pendingConnection) {
            // Complete connection
            const fromNode = this.pendingConnection.nodeId;
            const fromType = this.pendingConnection.type;
            const toType = connector.dataset.connectionType;

            console.log('Attempting connection from', fromNode, fromType, 'to', nodeId, toType);

            if (fromNode !== nodeId && fromType === 'output' && toType === 'input') {
                this.createConnection(fromNode, nodeId);
                console.log('Connection created successfully');
            } else {
                console.log('Connection not allowed');
            }

            this.clearPendingConnection();
        } else {
            // Start connection
            if (connector.dataset.connectionType === 'output') {
                this.pendingConnection = {
                    nodeId: nodeId,
                    type: 'output',
                    connector: connector
                };
                connector.classList.add('pending');
                console.log('Started connection from output connector');
            } else {
                console.log('Can only start connections from output connectors');
            }
        }
    }

    createConnection(fromNodeId, toNodeId) {
        // Check if connection already exists
        const exists = this.connections.some(conn =>
            conn.from === fromNodeId && conn.to === toNodeId
        );

        if (exists) return;

        // Remove any existing input connections to the target node
        this.connections = this.connections.filter(conn => {
            if (conn.to === toNodeId) {
                // Remove the SVG line element for the old connection
                if (conn.lineElement) {
                    conn.lineElement.remove();
                }
                return false;
            }
            return true;
        });

        // Create the new connection with its own line element
        const connectionData = {
            from: fromNodeId,
            to: toNodeId,
            lineElement: null
        };

        this.connections.push(connectionData);

        // Create the persistent line element
        this.createConnectionLine(connectionData);

        this.updateStatus();
        this.updateAllInheritedTemperatures();
    }

    clearPendingConnection() {
        if (this.pendingConnection) {
            this.pendingConnection.connector.classList.remove('pending');
            this.pendingConnection = null;
        }
        this.hidePreviewLine();
    }

    createConnectionLine(connectionData) {
        const fromNode = this.nodes.get(connectionData.from);
        const toNode = this.nodes.get(connectionData.to);

        if (!fromNode || !toNode) return;

        // Create the line element
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('stroke', '#007bff');
        line.setAttribute('stroke-width', '2');
        line.setAttribute('marker-end', 'url(#arrowhead)');

        // Set initial position
        this.updateConnectionLinePosition(connectionData, line);

        // Store the line element reference
        connectionData.lineElement = line;

        // Add to SVG
        this.connectionSvg.appendChild(line);
    }

    updateConnectionLinePosition(connectionData, line) {
        const fromNode = this.nodes.get(connectionData.from);
        const toNode = this.nodes.get(connectionData.to);

        if (!fromNode || !toNode) return;

        const fromPos = this.getConnectorPosition(fromNode, 'start');
        const toPos = this.getConnectorPosition(toNode, 'end');

        line.setAttribute('x1', fromPos.x);
        line.setAttribute('y1', fromPos.y);
        line.setAttribute('x2', toPos.x);
        line.setAttribute('y2', toPos.y);
    }

    redrawConnections() {
        // Update positions of existing line elements (with animation)
        this.connections.forEach(conn => {
            if (conn.lineElement) {
                this.updateConnectionLinePosition(conn, conn.lineElement);
            }
        });
    }


    selectNode(nodeId) {
        // Clear previous selection
        document.querySelectorAll('.flow-node.selected').forEach(node => {
            node.classList.remove('selected');
        });

        const nodeData = this.nodes.get(nodeId);
        if (nodeData) {
            nodeData.element.classList.add('selected');
            this.selectedNode = nodeId;
            this.showNodeProperties(nodeData);
        }
    }

    showNodeProperties(nodeData) {
        const panel = document.getElementById('nodeProperties');
        let templateId;

        // Map node types to template IDs
        switch(nodeData.type) {
            case 'start-node':
                templateId = 'startNodeProps';
                break;
            case 'temperature-goal':
                templateId = 'temperatureGoalProps';
                break;
            case 'temperature-hold':
                templateId = 'temperatureHoldProps';
                break;
            case 'end-node':
                templateId = 'endNodeProps';
                break;
            default:
                templateId = null;
        }

        const template = document.getElementById(templateId);

        if (template) {
            panel.innerHTML = template.innerHTML;
            this.populateProperties(nodeData);
            this.bindPropertyEvents(nodeData);
        }
    }

    populateProperties(nodeData) {
        const props = nodeData.properties;

        // Map properties to actual HTML input IDs
        const fieldMappings = {
            'start-node': {
                'initialTemperature': 'startNodeInitialTemp',
                'readCurrent': 'startNodeReadCurrent'
            },
            'temperature-goal': {
                'temperature': 'tempGoalValue',
                'tolerance': 'tempGoalTolerance'
            },
            'temperature-hold': {
                'duration': 'tempHoldDuration',
                'tolerance': 'tempHoldTolerance'
            },
            'end-node': {
                'cooldown': 'endNodeCooldown'
            }
        };

        const mapping = fieldMappings[nodeData.type];
        if (mapping) {
            Object.keys(props).forEach(key => {
                const inputId = mapping[key];
                const input = document.getElementById(inputId);
                if (input) {
                    if (input.type === 'checkbox') {
                        input.checked = props[key];
                    } else {
                        input.value = props[key];
                    }
                }
            });
        }

        // If this is a temperature hold node, show inherited temperature
        if (nodeData.type === 'temperature-hold') {
            this.updateInheritedTemperature(nodeData);
        }
    }

    updateInheritedTemperature(nodeData) {
        const inheritedTemp = this.getInheritedTemperature(nodeData.id);
        const display = document.getElementById('inheritedTempValue');

        if (display) {
            if (inheritedTemp === 'current') {
                display.textContent = 'Current chamber temp';
                display.style.color = 'var(--success-color, #28a745)';
            } else if (inheritedTemp !== null) {
                display.textContent = `${inheritedTemp}°C`;
                display.style.color = 'var(--primary-color, #007bff)';
            } else {
                display.textContent = 'Not connected';
                display.style.color = 'var(--text-muted, #666)';
            }
        }
    }

    getInheritedTemperature(nodeId) {
        // Find the connection that leads to this node
        const incomingConnection = this.connections.find(conn => conn.to === nodeId);

        if (!incomingConnection) {
            return null; // No incoming connection
        }

        const previousNode = this.nodes.get(incomingConnection.from);
        if (!previousNode) {
            return null;
        }

        // Get temperature from previous node
        if (previousNode.type === 'start-node') {
            return previousNode.properties.readCurrent ?
                'current' : // Special value indicating current temperature should be read
                (previousNode.properties.initialTemperature || 20);
        } else if (previousNode.type === 'temperature-goal') {
            return previousNode.properties.temperature || 20;
        } else if (previousNode.type === 'temperature-hold') {
            // Recursively get inherited temperature from previous node
            return this.getInheritedTemperature(previousNode.id);
        }

        return null;
    }

    updateAllInheritedTemperatures() {
        // Update inherited temperatures for all temperature-hold nodes
        this.nodes.forEach(node => {
            if (node.type === 'temperature-hold') {
                // If this node is currently selected, update its display
                if (this.selectedNode === node.id) {
                    this.updateInheritedTemperature(node);
                }
            }
        });
    }

    bindPropertyEvents(nodeData) {
        const inputs = document.querySelectorAll('#nodeProperties input');
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                this.updateNodeProperty(nodeData, input);
            });
        });
    }

    updateNodeProperty(nodeData, input) {
        // Reverse map from input ID to property name
        const fieldMappings = {
            'start-node': {
                'startNodeInitialTemp': 'initialTemperature',
                'startNodeReadCurrent': 'readCurrent'
            },
            'temperature-goal': {
                'tempGoalValue': 'temperature',
                'tempGoalTolerance': 'tolerance'
            },
            'temperature-hold': {
                'tempHoldDuration': 'duration',
                'tempHoldTolerance': 'tolerance'
            },
            'end-node': {
                'endNodeCooldown': 'cooldown'
            }
        };

        const mapping = fieldMappings[nodeData.type];
        const propName = mapping ? mapping[input.id] : null;

        if (propName) {
            const value = input.type === 'checkbox' ? input.checked :
                         input.type === 'number' ? parseFloat(input.value) : input.value;

            nodeData.properties[propName] = value;
            this.updateStatus();
            this.updateAllInheritedTemperatures();
        }
    }

    deleteNode(nodeId) {
        const nodeData = this.nodes.get(nodeId);
        if (nodeData) {
            // Remove node element
            nodeData.element.remove();

            // Remove connections and their line elements
            this.connections = this.connections.filter(conn => {
                if (conn.from === nodeId || conn.to === nodeId) {
                    // Remove the line element
                    if (conn.lineElement) {
                        conn.lineElement.remove();
                    }
                    return false;
                }
                return true;
            });

            // Remove from nodes map
            this.nodes.delete(nodeId);

            // Clear selection if this node was selected
            if (this.selectedNode === nodeId) {
                this.selectedNode = null;
                document.getElementById('nodeProperties').innerHTML =
                    '<p class="no-selection">Select a node to edit its properties</p>';
            }

            this.redrawConnections();
            this.updateStatus();
            this.updateAllInheritedTemperatures();
        }
    }

    clearCanvas() {
        if (confirm('Are you sure you want to clear the entire canvas?')) {
            // Clean up all line elements
            this.connections.forEach(conn => {
                if (conn.lineElement) {
                    conn.lineElement.remove();
                }
            });

            this.nodes.clear();
            this.connections = [];
            this.selectedNode = null;
            this.canvas.innerHTML = '';

            // Re-create the SVG with just the defs
            this.connectionSvg.innerHTML = `
                <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="7"
                            refX="9" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#007bff" />
                    </marker>
                </defs>
            `;

            document.getElementById('nodeProperties').innerHTML =
                '<p class="no-selection">Select a node to edit its properties</p>';
            this.updateStatus();
        }
    }

    validateFlow() {
        const validation = this.performValidation();

        if (validation.valid) {
            this.showMessage('Flow validation successful!', 'success');
        } else {
            this.showMessage(`Validation failed: ${validation.errors.join(', ')}`, 'error');
        }

        return validation;
    }

    performValidation() {
        const errors = [];

        // Check if flow is empty
        if (this.nodes.size === 0) {
            errors.push('Flow is empty');
            return { valid: false, errors };
        }

        // Check for start node
        const hasStartNode = Array.from(this.nodes.values()).some(node => node.type === 'start-node');
        if (!hasStartNode) {
            errors.push('Flow must have a start node');
        }

        // Check for end node
        const hasEndNode = Array.from(this.nodes.values()).some(node => node.type === 'end-node');
        if (!hasEndNode) {
            errors.push('Flow must have an end node');
        }

        // Check for disconnected nodes
        const connectedNodes = new Set();
        this.connections.forEach(conn => {
            connectedNodes.add(conn.from);
            connectedNodes.add(conn.to);
        });

        const disconnectedNodes = Array.from(this.nodes.keys()).filter(id =>
            !connectedNodes.has(id) && this.nodes.size > 1
        );

        if (disconnectedNodes.length > 0) {
            errors.push('All nodes must be connected');
        }

        // Validate node properties
        this.nodes.forEach(node => {
            const validation = this.validateNodeProperties(node);
            if (!validation.valid) {
                errors.push(...validation.errors);
            }
        });

        return { valid: errors.length === 0, errors };
    }

    validateNodeProperties(node) {
        const errors = [];
        const props = node.properties;

        if (node.type === 'start-node') {
            if (!props.readCurrent && (props.initialTemperature < this.config.minTemp || props.initialTemperature > this.config.maxTemp)) {
                errors.push(`Initial temperature out of range (${this.config.minTemp}°C to ${this.config.maxTemp}°C)`);
            }
        }

        if (node.type === 'temperature-goal') {
            if (props.temperature < this.config.minTemp || props.temperature > this.config.maxTemp) {
                errors.push(`Temperature out of range (${this.config.minTemp}°C to ${this.config.maxTemp}°C)`);
            }
        }

        if (node.type === 'temperature-hold') {
            // Validate inherited temperature
            const inheritedTemp = this.getInheritedTemperature(node.id);
            if (inheritedTemp === null) {
                errors.push(`Temperature hold node must be connected to receive temperature`);
            } else if (inheritedTemp < this.config.minTemp || inheritedTemp > this.config.maxTemp) {
                errors.push(`Inherited temperature out of range (${this.config.minTemp}°C to ${this.config.maxTemp}°C)`);
            }

            // Validate duration
            if (props.duration < 1 || props.duration > this.config.maxHoldTime) {
                errors.push(`Hold duration out of range (1 to ${this.config.maxHoldTime} minutes)`);
            }
        }

        return { valid: errors.length === 0, errors };
    }

    async exportFlow() {
        const validation = this.validateFlow();
        if (!validation.valid) {
            this.showMessage('Cannot export invalid flow. Please fix validation errors first.', 'error');
            return;
        }

        const flowData = this.serializeFlow();

        try {
            const response = await fetch('/store-flow-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(flowData)
            });

            const result = await response.json();

            if (response.ok) {
                this.showMessage('Flow exported successfully!', 'success');
            } else {
                this.showMessage(`Export failed: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showMessage(`Export failed: ${error.message}`, 'error');
        }
    }

    serializeFlow() {
        const nodes = Array.from(this.nodes.values()).map(node => {
            const serializedNode = {
                id: node.id,
                type: node.type,
                x: node.x,
                y: node.y,
                properties: { ...node.properties }
            };

            // Add inherited temperature for temperature-hold nodes
            if (node.type === 'temperature-hold') {
                const inheritedTemp = this.getInheritedTemperature(node.id);
                serializedNode.inheritedTemperature = inheritedTemp;
            }

            return serializedNode;
        });

        return {
            nodes: nodes,
            connections: [...this.connections],
            created: new Date().toISOString()
        };
    }

    updateStatus() {
        document.getElementById('nodeCount').textContent = this.nodes.size;

        const validation = this.performValidation();
        document.getElementById('flowStatus').textContent = validation.valid ? 'Valid' : 'Invalid';
        document.getElementById('flowStatus').className = `status-value ${validation.valid ? 'valid' : 'invalid'}`;

        // Calculate estimated duration
        let totalDuration = 0;
        this.nodes.forEach(node => {
            if (node.type === 'temperature-hold' && node.properties.duration) {
                totalDuration += node.properties.duration;
            }
        });

        if (totalDuration > 0) {
            const hours = Math.floor(totalDuration / 60);
            const minutes = totalDuration % 60;
            document.getElementById('estimatedDuration').textContent =
                hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
        } else {
            document.getElementById('estimatedDuration').textContent = 'Variable';
        }
    }

    showMessage(message, type) {
        // Create a temporary message element
        const messageEl = document.createElement('div');
        messageEl.className = `message ${type}`;
        messageEl.textContent = message;
        messageEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            border-radius: 4px;
            z-index: 2000;
            color: white;
            background: ${type === 'success' ? '#28a745' : '#dc3545'};
        `;

        document.body.appendChild(messageEl);

        setTimeout(() => {
            messageEl.remove();
        }, 3000);
    }

    handleCanvasClick(e) {
        if (e.target === this.canvas) {
            // Deselect all nodes
            document.querySelectorAll('.flow-node.selected').forEach(node => {
                node.classList.remove('selected');
            });
            this.selectedNode = null;
            document.getElementById('nodeProperties').innerHTML =
                '<p class="no-selection">Select a node to edit its properties</p>';
        }

        this.clearPendingConnection();
    }
}

// Initialize the flow designer when the page loads
let flowDesigner;
document.addEventListener('DOMContentLoaded', () => {
    flowDesigner = new FlowDesigner();
});