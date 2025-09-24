class FlowDesigner {
    constructor() {
        this.nodes = new Map();
        this.connections = [];
        this.selectedNode = null;
        this.nodeCounter = 0;
        this.draggedElement = null;
        this.currentFlowName = null;
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
        this.initializeSVG();
        this.updateStatus();
        this.startTemperatureUpdates();
    }

    initializeSVG() {
        // Ensure SVG has proper dimensions
        const canvasRect = this.canvas.getBoundingClientRect();
        if (canvasRect.width > 0 && canvasRect.height > 0) {
            this.connectionSvg.setAttribute('width', canvasRect.width);
            this.connectionSvg.setAttribute('height', canvasRect.height);
            this.connectionSvg.style.width = '100%';
            this.connectionSvg.style.height = '100%';
        } else {
            // If canvas isn't rendered yet, set a reasonable default and fix later
            this.connectionSvg.setAttribute('width', '100%');
            this.connectionSvg.setAttribute('height', '100%');
            this.connectionSvg.style.width = '100%';
            this.connectionSvg.style.height = '100%';
        }
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
        document.getElementById('saveFlow').addEventListener('click', () => this.saveFlow());
        document.getElementById('loadFlow').addEventListener('click', () => this.loadFlow());
        document.getElementById('exportFlow').addEventListener('click', () => this.exportFlow());

        // Canvas events
        this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));

        // Window resize
        window.addEventListener('resize', () => {
            this.initializeSVG();
            this.redrawConnections();
        });
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
            'start-node': { icon: '▶', label: 'Start' },
            'temperature-goal': { icon: '◎', label: 'Temp Goal' },
            'temperature-hold': { icon: '⏸', label: 'Temp Hold' },
            'end-node': { icon: '■', label: 'End' }
        };
        return configs[type] || { icon: '?', label: 'Unknown' };
    }

    getDefaultProperties(type) {
        const defaults = {
            'start-node': { readCurrent: true },
            'temperature-goal': { temperature: 20, tolerance: 0.5, estimatedDuration: 0 },
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

        // Recalculate estimated durations for all temperature-goal nodes downstream
        // (connection change affects all nodes after it)
        this.recalculateAllEstimatedDurations();
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

        if (!fromNode || !toNode) {
            console.error('createConnectionLine: Missing nodes', connectionData);
            return;
        }

        // Create the line element
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('stroke', '#007bff');
        line.setAttribute('stroke-width', '2');
        line.setAttribute('marker-end', 'url(#arrowhead)');
        line.setAttribute('opacity', '1');
        line.style.pointerEvents = 'none';

        // Set initial position
        this.updateConnectionLinePosition(connectionData, line);

        // Store the line element reference
        connectionData.lineElement = line;

        // Add to SVG
        this.connectionSvg.appendChild(line);

        console.log('Created SVG line element:', line, 'SVG container:', this.connectionSvg);
        console.log('Line attributes:', {
            x1: line.getAttribute('x1'),
            y1: line.getAttribute('y1'),
            x2: line.getAttribute('x2'),
            y2: line.getAttribute('y2'),
            stroke: line.getAttribute('stroke')
        });
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

            // Update temperature immediately if start node is selected
            if (nodeData.type === 'start-node') {
                this.updateStartNodeTemperature();
            }
        }
    }

    populateProperties(nodeData) {
        const props = nodeData.properties;

        // Map properties to actual HTML input IDs
        const fieldMappings = {
            'start-node': {
                // No configurable properties for start node
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

        // If this is a temperature-goal node, show/update estimated duration
        if (nodeData.type === 'temperature-goal') {
            const durationDisplay = document.getElementById('tempGoalEstimatedDuration');
            if (durationDisplay) {
                const duration = nodeData.properties.estimatedDuration || 0;
                if (duration > 0) {
                    durationDisplay.textContent = `${duration} min`;
                } else {
                    durationDisplay.textContent = 'Unknown';
                }
            }
            // Recalculate duration in case connections have changed
            this.calculateAndUpdateEstimatedDuration(nodeData);
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
                // No configurable properties for start node
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

            // Recalculate estimated duration for temperature-goal nodes when temperature changes
            if (nodeData.type === 'temperature-goal' && propName === 'temperature') {
                this.calculateAndUpdateEstimatedDuration(nodeData);
            }

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

            // Recalculate durations for remaining nodes
            this.recalculateAllEstimatedDurations();

            this.redrawConnections();
            this.updateStatus();
            this.updateAllInheritedTemperatures();
        }
    }

    clearCanvas(showConfirm = true) {
        if (!showConfirm || confirm('Are you sure you want to clear the entire canvas?')) {
            // Clean up all line elements
            this.connections.forEach(conn => {
                if (conn.lineElement) {
                    conn.lineElement.remove();
                }
            });

            this.nodes.clear();
            this.connections = [];
            this.selectedNode = null;
            this.currentFlowName = null;

            // Clear only the flow nodes, but preserve the SVG
            const flowNodes = this.canvas.querySelectorAll('.flow-node');
            flowNodes.forEach(node => node.remove());

            // Clear the SVG content but keep the SVG element itself
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

    /**
     * Show flow selection modal
     */
    showFlowSelectionModal(flows) {
        const modalHtml = `
            <div id="flowSelectionModal" class="flow-selection-modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Load Flow Diagram</h3>
                        <button class="modal-close" onclick="this.closest('.flow-selection-modal').remove()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="flow-list">
                            ${flows.map(flow => `
                                <div class="flow-item" data-flow-id="${flow.id}">
                                    <div class="flow-info">
                                        <div class="flow-name">${flow.name}</div>
                                        <div class="flow-details">
                                            <span>Created: ${new Date(flow.created).toLocaleDateString()}</span>
                                            <span>Modified: ${new Date(flow.lastModified).toLocaleDateString()}</span>
                                            <span>Nodes: ${flow.metadata.nodeCount}</span>
                                        </div>
                                    </div>
                                    <div class="flow-actions">
                                        <button onclick="flowDesigner.loadSelectedFlow('${flow.id}')" class="btn-load">Load</button>
                                        <button onclick="flowDesigner.deleteFlow('${flow.id}')" class="btn-delete">Delete</button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button onclick="this.closest('.flow-selection-modal').remove()">Cancel</button>
                    </div>
                </div>
            </div>
        `;

        // Add modal styles if not already present
        if (!document.getElementById('flowSelectionModalStyles')) {
            const styles = document.createElement('style');
            styles.id = 'flowSelectionModalStyles';
            styles.textContent = `
                .flow-selection-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 10000;
                }
                .flow-selection-modal .modal-content {
                    background: var(--card-background);
                    color: var(--text-color);
                    border-radius: 8px;
                    width: 90%;
                    max-width: 600px;
                    max-height: 80%;
                    overflow-y: auto;
                    box-shadow: 0 4px 6px var(--shadow-color);
                    border: 1px solid var(--border-color);
                }
                .flow-selection-modal .modal-header {
                    padding: 20px;
                    border-bottom: 1px solid var(--border-color);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .flow-selection-modal .modal-header h3 {
                    color: var(--text-color);
                    margin: 0;
                }
                .flow-selection-modal .modal-close {
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: var(--text-color);
                }
                .flow-selection-modal .modal-close:hover {
                    color: var(--danger-color);
                }
                .flow-selection-modal .modal-body {
                    padding: 20px;
                }
                .flow-selection-modal .flow-item {
                    border: 1px solid var(--border-color);
                    border-radius: 5px;
                    margin-bottom: 10px;
                    padding: 15px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background: var(--card-background);
                }
                .flow-selection-modal .flow-item:hover {
                    background: var(--background-color);
                }
                .flow-selection-modal .flow-name {
                    font-weight: bold;
                    margin-bottom: 5px;
                    color: var(--text-color);
                }
                .flow-selection-modal .flow-details {
                    font-size: 12px;
                    color: var(--text-color);
                    opacity: 0.7;
                }
                .flow-selection-modal .flow-details span {
                    margin-right: 15px;
                }
                .flow-selection-modal .flow-actions button {
                    margin-left: 10px;
                    padding: 5px 10px;
                    border: 1px solid var(--primary-color);
                    background: var(--primary-color);
                    color: white;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 12px;
                }
                .flow-selection-modal .flow-actions button:hover {
                    opacity: 0.9;
                }
                .flow-selection-modal .btn-delete {
                    background: var(--danger-color) !important;
                    border-color: var(--danger-color) !important;
                }
                .flow-selection-modal .modal-footer {
                    padding: 20px;
                    border-top: 1px solid var(--border-color);
                    text-align: right;
                }
                .flow-selection-modal .modal-footer button {
                    padding: 8px 16px;
                    border: 1px solid var(--border-color);
                    background: var(--card-background);
                    color: var(--text-color);
                    border-radius: 4px;
                    cursor: pointer;
                }
                .flow-selection-modal .modal-footer button:hover {
                    background: var(--background-color);
                }
            `;
            document.head.appendChild(styles);
        }

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    /**
     * Load selected flow from modal
     */
    async loadSelectedFlow(flowId) {
        try {
            const response = await fetch(`/get-flow-diagram/${flowId}`);
            const result = await response.json();

            if (response.ok) {
                this.loadFlowData(result.flowData);
                this.showMessage(`Flow "${result.flowData.name}" loaded successfully!`, 'success');

                // Close modal
                document.getElementById('flowSelectionModal')?.remove();
            } else {
                this.showMessage(`Load failed: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showMessage(`Load failed: ${error.message}`, 'error');
        }
    }

    /**
     * Delete flow
     */
    async deleteFlow(flowId) {
        if (!confirm('Are you sure you want to delete this flow?')) return;

        try {
            const response = await fetch(`/delete-flow-diagram/${flowId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (response.ok) {
                this.showMessage('Flow deleted successfully!', 'success');

                // Refresh the modal
                document.getElementById('flowSelectionModal')?.remove();
                this.loadFlow();
            } else {
                this.showMessage(`Delete failed: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showMessage(`Delete failed: ${error.message}`, 'error');
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
            } else if (inheritedTemp !== 'current' && (inheritedTemp < this.config.minTemp || inheritedTemp > this.config.maxTemp)) {
                errors.push(`Inherited temperature out of range (${this.config.minTemp}°C to ${this.config.maxTemp}°C)`);
            }

            // Validate duration
            if (props.duration < 1 || props.duration > this.config.maxHoldTime) {
                errors.push(`Hold duration out of range (1 to ${this.config.maxHoldTime} minutes)`);
            }
        }

        return { valid: errors.length === 0, errors };
    }

    /**
     * Export flow to server for execution
     */
    async exportFlow() {
        const validation = this.validateFlow();
        if (!validation.valid) {
            this.showMessage('Cannot export invalid flow. Please fix validation errors first.', 'error');
            return;
        }

        const flowData = this.serializeFlow();
        const executionFlow = await this.convertToExecutionFlow();

        // Send both the original flow data and the execution-ready format
        const exportData = {
            originalFlow: flowData,
            executionFlow: executionFlow,
            fullFlowData: this.getFullFlowData()
        };

        try {
            const response = await fetch('/store-flow-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(exportData)
            });

            const result = await response.json();

            if (response.ok) {
                this.showMessage('Flow exported to server successfully!', 'success');

                // Redirect to flow execution page if provided
                if (result.redirectTo) {
                    setTimeout(() => {
                        window.location.href = result.redirectTo;
                    }, 1500); // Give time to show the success message
                }
            } else {
                this.showMessage(`Export failed: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showMessage(`Export failed: ${error.message}`, 'error');
        }
    }

    /**
     * Save flow diagram to local storage with name prompt
     */
    async saveFlow() {
        const validation = this.validateFlow();
        if (!validation.valid) {
            this.showMessage('Cannot save invalid flow. Please fix validation errors first.', 'error');
            return;
        }

        const flowName = prompt('Enter a name for this flow:');
        if (!flowName) return;

        const fullFlowData = this.getFullFlowData();
        fullFlowData.name = flowName;
        fullFlowData.lastModified = new Date().toISOString();

        try {
            const response = await fetch('/save-flow-diagram', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(fullFlowData)
            });

            const result = await response.json();

            if (response.ok) {
                this.showMessage(`Flow "${flowName}" saved successfully!`, 'success');
                this.currentFlowName = flowName;
            } else {
                this.showMessage(`Save failed: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showMessage(`Save failed: ${error.message}`, 'error');
        }
    }

    /**
     * Load flow diagram from server
     */
    async loadFlow() {
        try {
            // First get list of available flows
            const response = await fetch('/get-saved-flows');
            const result = await response.json();

            if (!response.ok) {
                this.showMessage(`Failed to load flows: ${result.error}`, 'error');
                return;
            }

            const flows = result.flows;
            if (flows.length === 0) {
                this.showMessage('No saved flows found.', 'info');
                return;
            }

            // Show flow selection modal
            this.showFlowSelectionModal(flows);

        } catch (error) {
            this.showMessage(`Load failed: ${error.message}`, 'error');
        }
    }

    /**
     * Get complete flow data including all visual and logical information
     */
    getFullFlowData() {
        const nodes = Array.from(this.nodes.values()).map(node => ({
            id: node.id,
            type: node.type,
            x: node.x,
            y: node.y,
            properties: { ...node.properties }
        }));

        return {
            version: "1.0",
            created: new Date().toISOString(),
            nodes: nodes,
            connections: [...this.connections],
            metadata: {
                nodeCount: this.nodes.size,
                connectionCount: this.connections.length,
                canvasSize: {
                    width: this.canvas.clientWidth,
                    height: this.canvas.clientHeight
                }
            },
            executionFlow: this.convertToExecutionFlow()
        };
    }

    /**
     * Load flow data into the designer
     */
    loadFlowData(flowData) {
        // Clear existing flow
        this.clearCanvas(false); // Don't show confirmation

        // Restore nodes first
        flowData.nodes.forEach(nodeData => {
            // Use center coordinates for node creation
            const centerX = nodeData.x + 50; // Convert from left edge to center
            const centerY = nodeData.y + 25; // Convert from top edge to center

            const nodeElement = this.createNodeElement(nodeData.type, nodeData.id, centerX, centerY);

            // Extract the actual positioned coordinates from the element after creation
            const actualLeft = parseInt(nodeElement.style.left) || 0;
            const actualTop = parseInt(nodeElement.style.top) || 0;

            const node = {
                id: nodeData.id,
                type: nodeData.type,
                x: actualLeft, // Use actual element coordinates
                y: actualTop,  // Use actual element coordinates
                element: nodeElement,
                properties: { ...nodeData.properties }
            };

            this.nodes.set(nodeData.id, node);
            this.canvas.appendChild(nodeElement);

            console.log(`Restored node ${nodeData.id} at element position (${actualLeft}, ${actualTop}), original (${nodeData.x}, ${nodeData.y})`);
        });

        // Use setTimeout to ensure DOM elements are rendered before creating connections
        setTimeout(() => {
            console.log('SVG element:', this.connectionSvg);
            console.log('SVG dimensions:', {
                width: this.connectionSvg.clientWidth,
                height: this.connectionSvg.clientHeight,
                offsetWidth: this.connectionSvg.offsetWidth,
                offsetHeight: this.connectionSvg.offsetHeight
            });

            // Ensure SVG is properly initialized and sized
            if (!this.connectionSvg.querySelector('defs')) {
                this.connectionSvg.innerHTML = `
                    <defs>
                        <marker id="arrowhead" markerWidth="10" markerHeight="7"
                                refX="9" refY="3.5" orient="auto">
                            <polygon points="0 0, 10 3.5, 0 7" fill="#007bff" />
                        </marker>
                    </defs>
                `;
                console.log('Recreated SVG defs');
            }

            // Fix SVG dimensions - ensure it matches its parent container
            const canvasRect = this.canvas.getBoundingClientRect();
            this.connectionSvg.setAttribute('width', canvasRect.width);
            this.connectionSvg.setAttribute('height', canvasRect.height);
            this.connectionSvg.style.width = '100%';
            this.connectionSvg.style.height = '100%';

            // Ensure SVG is properly visible
            this.connectionSvg.style.visibility = 'visible';
            this.connectionSvg.style.display = 'block';
            this.connectionSvg.style.pointerEvents = 'none';

            console.log('Fixed SVG dimensions:', {
                canvasRect: canvasRect,
                svgWidth: this.connectionSvg.getAttribute('width'),
                svgHeight: this.connectionSvg.getAttribute('height'),
                svgRect: this.connectionSvg.getBoundingClientRect(),
                svgStyle: {
                    position: getComputedStyle(this.connectionSvg).position,
                    zIndex: getComputedStyle(this.connectionSvg).zIndex,
                    display: getComputedStyle(this.connectionSvg).display,
                    visibility: getComputedStyle(this.connectionSvg).visibility,
                    opacity: getComputedStyle(this.connectionSvg).opacity
                },
                canvasStyle: {
                    position: getComputedStyle(this.canvas).position,
                    overflow: getComputedStyle(this.canvas).overflow,
                    zIndex: getComputedStyle(this.canvas).zIndex,
                    display: getComputedStyle(this.canvas).display
                }
            });

            // Log all node positions before creating connections
            console.log('All nodes after loading:');
            this.nodes.forEach(node => {
                console.log(`Node ${node.id}:`, {
                    x: node.x,
                    y: node.y,
                    styleLeft: node.element.style.left,
                    styleTop: node.element.style.top,
                    boundingRect: node.element.getBoundingClientRect()
                });
            });

            // Restore connections after nodes are fully rendered
            flowData.connections.forEach((connData, index) => {
                const fromNode = this.nodes.get(connData.from);
                const toNode = this.nodes.get(connData.to);

                if (fromNode && toNode) {
                    const connectionData = {
                        from: connData.from,
                        to: connData.to,
                        lineElement: null
                    };

                    this.connections.push(connectionData);
                    this.createConnectionLine(connectionData);

                    // Debug connection positions
                    const fromPos = this.getConnectorPosition(fromNode, 'start');
                    const toPos = this.getConnectorPosition(toNode, 'end');
                    console.log(`Restored connection ${index + 1}:`, connData.from, '->', connData.to,
                               `from(${fromPos.x}, ${fromPos.y}) to(${toPos.x}, ${toPos.y})`);
                } else {
                    console.error(`Failed to restore connection ${index + 1}: missing nodes`, connData);
                }
            });

            // Force a redraw of all connections
            this.redrawConnections();

            console.log(`Loaded flow with ${this.nodes.size} nodes and ${this.connections.length} connections`);
            console.log('SVG children after loading:', this.connectionSvg.children);
        }, 200); // Increased timeout even more

        // Update counter and status
        this.nodeCounter = Math.max(...Array.from(this.nodes.keys()).map(id =>
            parseInt(id.replace('node_', '')) || 0
        ));

        this.updateStatus();

        // Set current flow name if available
        if (flowData.name) {
            this.currentFlowName = flowData.name;
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

    /**
     * Converts the flow diagram to an execution-ready JSON structure
     * Removes visual positioning and focuses on sequential execution order
     */
    async convertToExecutionFlow() {
        const validation = this.performValidation();
        if (!validation.valid) {
            throw new Error(`Cannot convert invalid flow: ${validation.errors.join(', ')}`);
        }

        // Find execution order by traversing from start node
        const executionOrder = this.determineExecutionOrder();

        // Get current chamber temperature for estimation
        let currentTemp = null;
        try {
            const tempResponse = await fetch('/get-current-chamber-temperature');
            const tempData = await tempResponse.json();
            if (tempData.success) {
                currentTemp = tempData.temperature;
            }
        } catch (error) {
            console.warn('Could not fetch current temperature:', error);
        }

        // Convert nodes to execution steps
        const executionSteps = executionOrder.map((nodeId, index) => {
            const node = this.nodes.get(nodeId);
            const prevNode = index > 0 ? this.nodes.get(executionOrder[index - 1]) : null;
            return this.convertNodeToExecutionStep(node, index, prevNode, currentTemp);
        });

        // Calculate total estimated duration
        const totalDuration = executionSteps.reduce((sum, step) => {
            return sum + (step.duration || 0);
        }, 0);

        return {
            version: "1.0",
            flowId: `flow_${Date.now()}`,
            created: new Date().toISOString(),
            metadata: {
                totalSteps: executionSteps.length,
                estimatedDurationMinutes: totalDuration,
                temperatureRange: this.getTemperatureRange(executionSteps)
            },
            executionSteps: executionSteps
        };
    }

    /**
     * Determines the execution order by traversing the flow graph from start to end
     */
    determineExecutionOrder() {
        // Find start node
        const startNode = Array.from(this.nodes.values()).find(node => node.type === 'start-node');
        if (!startNode) {
            throw new Error('No start node found');
        }

        const executionOrder = [];
        const visited = new Set();
        let currentNodeId = startNode.id;

        while (currentNodeId && !visited.has(currentNodeId)) {
            visited.add(currentNodeId);
            executionOrder.push(currentNodeId);

            // Find next node
            const nextConnection = this.connections.find(conn => conn.from === currentNodeId);
            currentNodeId = nextConnection ? nextConnection.to : null;
        }

        return executionOrder;
    }

    /**
     * Converts a flow node to an execution step
     */
    convertNodeToExecutionStep(node, stepIndex, prevNode = null, currentTemp = null) {
        const baseStep = {
            stepId: stepIndex + 1,
            stepType: node.type,
            description: this.getStepDescription(node)
        };

        switch (node.type) {
            case 'start-node':
                return {
                    ...baseStep,
                    action: 'initialize',
                    targetTemperature: null, // Start node never sets a target temperature
                    readCurrentTemperature: true, // Always read current temperature as starting point
                    duration: 0,
                    description: 'Initialize flow and read current chamber temperature'
                };

            case 'temperature-goal':
                // Use stored estimated duration if available, otherwise calculate
                const estimatedDuration = node.properties.estimatedDuration ||
                    this.calculateEstimatedDuration(prevNode, node.properties.temperature, currentTemp);
                return {
                    ...baseStep,
                    action: 'reach_temperature',
                    targetTemperature: node.properties.temperature,
                    tolerance: node.properties.tolerance,
                    duration: estimatedDuration, // Estimated duration in minutes
                    maxWaitTime: 60 // Maximum time to wait for temperature to be reached (minutes)
                };

            case 'temperature-hold':
                const inheritedTemp = this.getInheritedTemperature(node.id);
                return {
                    ...baseStep,
                    action: 'hold_temperature',
                    targetTemperature: inheritedTemp === 'current' ? null : inheritedTemp,
                    readCurrentTemperature: inheritedTemp === 'current',
                    tolerance: node.properties.tolerance,
                    duration: node.properties.duration
                };

            case 'end-node':
                return {
                    ...baseStep,
                    action: 'finalize',
                    cooldown: node.properties.cooldown,
                    duration: node.properties.cooldown ? 10 : 0 // 10 minutes cooldown if enabled
                };

            default:
                throw new Error(`Unknown node type: ${node.type}`);
        }
    }

    /**
     * Generates a human-readable description for each step
     */
    getStepDescription(node) {
        switch (node.type) {
            case 'start-node':
                if (node.properties.readCurrent) {
                    return 'Initialize flow using current chamber temperature';
                } else {
                    return `Initialize flow with temperature ${node.properties.initialTemperature}°C`;
                }

            case 'temperature-goal':
                return `Reach target temperature ${node.properties.temperature}°C (±${node.properties.tolerance}°C)`;

            case 'temperature-hold':
                const inheritedTemp = this.getInheritedTemperature(node.id);
                const tempText = inheritedTemp === 'current' ? 'current temperature' : `${inheritedTemp}°C`;
                return `Hold ${tempText} for ${node.properties.duration} minutes (±${node.properties.tolerance}°C)`;

            case 'end-node':
                return node.properties.cooldown ? 'End flow with cooldown' : 'End flow immediately';

            default:
                return 'Unknown step';
        }
    }

    /**
     * Recalculate estimated durations for all temperature-goal nodes
     */
    async recalculateAllEstimatedDurations() {
        for (const node of this.nodes.values()) {
            if (node.type === 'temperature-goal') {
                await this.calculateAndUpdateEstimatedDuration(node);
            }
        }
    }

    /**
     * Calculate and update estimated duration for a temperature-goal node
     */
    async calculateAndUpdateEstimatedDuration(nodeData) {
        if (nodeData.type !== 'temperature-goal') return;

        // Find the previous node
        const incomingConnection = this.connections.find(conn => conn.to === nodeData.id);
        const prevNode = incomingConnection ? this.nodes.get(incomingConnection.from) : null;

        // If no previous node is connected, cannot estimate duration
        if (!prevNode) {
            nodeData.properties.estimatedDuration = 0;

            // Update the UI if this node is currently selected
            const durationDisplay = document.getElementById('tempGoalEstimatedDuration');
            if (durationDisplay) {
                durationDisplay.textContent = 'Not connected';
            }

            // Update total flow duration in status bar
            this.updateStatus();

            console.log(`Cannot estimate duration for ${nodeData.id} - no incoming connection`);
            return;
        }

        // Get current temperature if needed
        let currentTemp = null;
        if (prevNode.type === 'start-node' && prevNode.properties.readCurrent) {
            try {
                const response = await fetch('/get-current-chamber-temperature');
                const data = await response.json();
                if (data.success) {
                    currentTemp = data.temperature;
                }
            } catch (error) {
                console.warn('Could not fetch temperature for estimation:', error);
            }
        }

        // Calculate duration
        const duration = this.calculateEstimatedDuration(prevNode, nodeData.properties.temperature, currentTemp);

        // Store in node properties
        nodeData.properties.estimatedDuration = duration;

        // Update the UI if this node is currently selected
        const durationDisplay = document.getElementById('tempGoalEstimatedDuration');
        if (durationDisplay) {
            if (duration > 0) {
                durationDisplay.textContent = `${duration} min`;
            } else {
                durationDisplay.textContent = 'Unknown';
            }
        }

        // Update total flow duration in status bar
        this.updateStatus();

        console.log(`Updated estimated duration for ${nodeData.id}:`, duration, 'minutes');
    }

    /**
     * Calculate estimated duration to reach target temperature
     */
    calculateEstimatedDuration(prevNode, targetTemp, currentTemp) {
        let startTemp = currentTemp;

        // Determine starting temperature
        if (prevNode) {
            if (prevNode.type === 'start-node') {
                if (prevNode.properties.readCurrent && currentTemp !== null) {
                    startTemp = currentTemp;
                } else if (!prevNode.properties.readCurrent) {
                    startTemp = prevNode.properties.initialTemperature;
                }
            } else if (prevNode.type === 'temperature-goal') {
                startTemp = prevNode.properties.temperature;
            } else if (prevNode.type === 'temperature-hold') {
                const inheritedTemp = this.getInheritedTemperature(prevNode.id);
                startTemp = inheritedTemp === 'current' ? currentTemp : inheritedTemp;
            }
        }

        // If we can't determine start temperature, return 0 (unknown)
        if (startTemp === null || startTemp === undefined || startTemp === 'current') {
            console.log('Cannot estimate duration - unknown start temp:', { prevNode: prevNode?.type, startTemp, targetTemp, currentTemp });
            return 0;
        }

        const tempDifference = Math.abs(targetTemp - startTemp);
        const isHeating = targetTemp > startTemp;

        // Get max rate from config (degrees per minute)
        const maxRate = isHeating ?
            (this.config.max_rico_heating || 10) :
            (this.config.max_rico_cooling || 10);

        // Get curve factor (0-1, where lower=more curved, 1=linear)
        const curveFactor = isHeating ?
            (this.config.heating_curve_factor || 0.6) :
            (this.config.cooling_curve_factor || 0.7);

        // Calculate estimated time in minutes with non-linear curve factor
        // The curve factor adjusts for slower approach to target temperature
        // Lower curve factor = more time needed (exponential slowdown)
        const linearTime = tempDifference / maxRate;
        const estimatedMinutes = Math.ceil(linearTime / curveFactor);

        console.log('Estimated duration:', {
            startTemp,
            targetTemp,
            tempDifference,
            isHeating,
            maxRate,
            curveFactor,
            linearTime,
            estimatedMinutes
        });

        return estimatedMinutes;
    }

    /**
     * Calculates the temperature range used in the flow
     */
    getTemperatureRange(executionSteps) {
        const temperatures = executionSteps
            .filter(step => step.targetTemperature !== null && step.targetTemperature !== undefined)
            .map(step => step.targetTemperature);

        if (temperatures.length === 0) {
            return { min: null, max: null };
        }

        return {
            min: Math.min(...temperatures),
            max: Math.max(...temperatures)
        };
    }

    /**
     * Start periodic temperature updates for start nodes
     */
    startTemperatureUpdates() {
        // Update immediately
        this.updateStartNodeTemperature();

        // Then update every 5 seconds
        this.temperatureUpdateInterval = setInterval(() => {
            this.updateStartNodeTemperature();
        }, 5000);
    }

    /**
     * Update temperature display in properties panel
     */
    async updateStartNodeTemperature() {
        try {
            const response = await fetch('/get-current-chamber-temperature');
            const data = await response.json();

            const tempDisplay = document.getElementById('currentChamberTemp');
            if (!tempDisplay) return; // Element not in DOM (no start node selected)

            if (data.success) {
                tempDisplay.textContent = `${data.temperature.toFixed(1)}°C`;
                tempDisplay.style.color = '#4CAF50';
            } else {
                tempDisplay.textContent = 'N/A';
                tempDisplay.style.color = '#999';
            }
        } catch (error) {
            const tempDisplay = document.getElementById('currentChamberTemp');
            if (tempDisplay) {
                tempDisplay.textContent = 'Error fetching temperature';
                tempDisplay.style.color = '#dc3545';
            }
        }
    }

    updateStatus() {
        document.getElementById('nodeCount').textContent = this.nodes.size;

        const validation = this.performValidation();
        document.getElementById('flowStatus').textContent = validation.valid ? 'Valid' : 'Invalid';
        document.getElementById('flowStatus').className = `status-value ${validation.valid ? 'valid' : 'invalid'}`;

        // Calculate total estimated duration (temperature-hold + temperature-goal durations)
        let totalDuration = 0;
        let hasUnknownDurations = false;

        this.nodes.forEach(node => {
            if (node.type === 'temperature-hold' && node.properties.duration) {
                totalDuration += node.properties.duration;
            } else if (node.type === 'temperature-goal') {
                const estimatedDuration = node.properties.estimatedDuration || 0;
                if (estimatedDuration > 0) {
                    totalDuration += estimatedDuration;
                } else {
                    hasUnknownDurations = true;
                }
            }
        });

        const durationElement = document.getElementById('estimatedDuration');
        if (totalDuration > 0) {
            const hours = Math.floor(totalDuration / 60);
            const minutes = Math.round(totalDuration % 60);
            let durationText = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

            // Add "+" if there are unknown durations
            if (hasUnknownDurations) {
                durationText += '+';
            }

            durationElement.textContent = durationText;
        } else if (hasUnknownDurations) {
            durationElement.textContent = 'Calculating...';
        } else {
            durationElement.textContent = '--';
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