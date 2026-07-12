// State Variables
let network = null;
let nodesDataSet = new vis.DataSet([]);
let edgesDataSet = new vis.DataSet([]);
let chatHistory = [];
let allNodesMap = {}; // Keep trace of all nodes by ID

// DOM Elements
const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const totalNodesVal = document.getElementById('total-nodes-val');
const totalEdgesVal = document.getElementById('total-edges-val');
const btnFullGraph = document.getElementById('btn-full-graph');
const btnReset = document.getElementById('btn-reset');
const detailsCard = document.getElementById('details-card');
const detailsTitle = document.getElementById('details-title');
const detailsCategory = document.getElementById('details-category');
const detailsDesc = document.getElementById('details-desc');
const closeDetailsBtn = document.getElementById('close-details-btn');
const queriesContent = document.getElementById('queries-content');
const toggleQueriesBtn = document.getElementById('toggle-queries-btn');
const queriesPanel = document.querySelector('.queries-panel');
const loadingOverlay = document.getElementById('loading-overlay');
const statusText = document.getElementById('status-text');
const statusDot = document.querySelector('.status-dot');

// Group Color Mapping for Vis.js
const groupStyles = {
    CoreAI: { color: { background: '#141E33', border: '#38BDF8', hover: '#38BDF8', highlight: { background: '#141E33', border: '#00F2FE' } } },
    NLP: { color: { background: '#1A1835', border: '#C084FC', hover: '#C084FC', highlight: { background: '#1A1835', border: '#7C3AED' } } },
    Database: { color: { background: '#112224', border: '#34D399', hover: '#34D399', highlight: { background: '#112224', border: '#059669' } } },
    RAG: { color: { background: '#241427', border: '#F472B6', hover: '#F472B6', highlight: { background: '#241427', border: '#DB2777' } } },
    Framework: { color: { background: '#271914', border: '#FB923C', hover: '#FB923C', highlight: { background: '#271914', border: '#EA580C' } } },
    Discovered: { color: { background: '#262211', border: '#FBBF24', hover: '#FBBF24', highlight: { background: '#262211', border: '#D97706' } } },
    Concept: { color: { background: '#1E293B', border: '#9CA3AF', hover: '#9CA3AF', highlight: { background: '#1E293B', border: '#4B5563' } } }
};

// Initialize Vis.js Network
function initNetwork() {
    const container = document.getElementById('graph-canvas');
    const data = {
        nodes: nodesDataSet,
        edges: edgesDataSet
    };
    
    const options = {
        nodes: {
            shape: 'dot',
            size: 20,
            font: {
                size: 13,
                color: '#E5E7EB',
                face: 'Outfit',
                bold: {
                    color: '#FFFFFF'
                }
            },
            borderWidth: 2.5,
            shadow: {
                enabled: true,
                color: 'rgba(0, 0, 0, 0.4)',
                size: 8,
                x: 0,
                y: 3
            }
        },
        edges: {
            width: 2.5,
            color: {
                color: 'rgba(255, 255, 255, 0.12)',
                highlight: '#00F2FE',
                hover: '#00F2FE'
            },
            arrows: {
                to: { enabled: true, scaleFactor: 0.6 }
            },
            smooth: {
                type: 'cubicBezier',
                forceDirection: 'none',
                roundness: 0.45
            },
            font: {
                size: 10,
                color: '#9CA3AF',
                face: 'Outfit',
                align: 'middle'
            }
        },
        groups: groupStyles,
        physics: {
            barnesHut: {
                gravitationalConstant: -3500,
                centralGravity: 0.35,
                springLength: 100,
                springConstant: 0.04,
                damping: 0.1,
                avoidOverlap: 0.25
            },
            stabilization: {
                enabled: true,
                iterations: 120,
                fit: true
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 100
        }
    };

    network = new vis.Network(container, data, options);

    // Network Events
    network.on("selectNode", function (params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            showNodeDetails(nodeId);
        }
    });

    network.on("deselectNode", function () {
        hideNodeDetails();
    });
}

// Fetch and Render Full Graph
async function loadFullGraph() {
    showLoading(true, "Loading Full Knowledge Graph...");
    try {
        const response = await fetch('/api/graph');
        if (!response.ok) throw new Error("API call failed");
        const data = await response.json();
        
        renderGraphData(data);
        updateStatus(true);
    } catch (error) {
        console.error("Error loading graph:", error);
        updateStatus(false);
    } finally {
        showLoading(false);
    }
}

// Populate datasets in Vis.js
function renderGraphData(graphData) {
    nodesDataSet.clear();
    edgesDataSet.clear();
    allNodesMap = {};

    // Map Nodes
    const nodes = graphData.nodes.map(n => {
        const props = n.properties || {};
        allNodesMap[n.id] = n;
        
        // Define Vis properties
        return {
            id: n.id,
            label: n.label, // Display name
            group: n.group || "Concept",
            title: props.description || "" // Tooltip
        };
    });

    // Map Edges
    const edges = graphData.edges.map(e => {
        return {
            id: e.id,
            from: e.from,
            to: e.to,
            label: e.label // Relation type (e.g. USES)
        };
    });

    nodesDataSet.add(nodes);
    edgesDataSet.add(edges);

    // Update Counters
    totalNodesVal.textContent = nodes.length;
    totalEdgesVal.textContent = edges.length;

    // Stabilize layout
    network.stabilize();
}

// Show details card for selected node
function showNodeDetails(nodeId) {
    const node = allNodesMap[nodeId];
    if (!node) return;

    const props = node.properties || {};
    detailsTitle.textContent = node.label;
    detailsCategory.textContent = node.group;
    detailsDesc.textContent = props.description || "No description provided.";
    
    // Change badge style based on group
    detailsCategory.style.borderColor = getCategoryBorderColor(node.group);
    
    detailsCard.classList.add('active');
}

function hideNodeDetails() {
    detailsCard.classList.remove('active');
}

function getCategoryBorderColor(group) {
    const style = groupStyles[group];
    return style ? style.color.border : '#9CA3AF';
}

// Toggle loading state
function showLoading(show, text = "Loading...") {
    loadingOverlay.querySelector('#loading-text').textContent = text;
    if (show) {
        loadingOverlay.classList.add('active');
    } else {
        loadingOverlay.classList.remove('active');
    }
}

// Toggle status indicator
function updateStatus(online) {
    if (online) {
        statusDot.className = 'status-dot online';
        statusText.textContent = 'Neo4j Connected';
    } else {
        statusDot.className = 'status-dot offline';
        statusText.textContent = 'Disconnected';
    }
}

// ==========================================================================
// Chat Functionality
// ==========================================================================

async function handleSendMessage(event) {
    event.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    // Clear input & disable interaction
    chatInput.value = '';
    chatInput.disabled = true;
    sendBtn.disabled = true;

    // Append User Message to UI
    appendMessage("user", query);
    
    // Append Typing indicator
    const typingIndicator = appendTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: query,
                history: chatHistory
            })
        });

        if (!response.ok) throw new Error("Server responded with error");
        const data = await response.json();

        // Remove typing indicator
        typingIndicator.remove();

        // Append Bot Response
        appendMessage("bot", data.response);

        // Update Chat history for context
        chatHistory.push({ role: "user", content: query });
        chatHistory.push({ role: "assistant", content: data.response });

        // Highlight/Insert returned subgraph nodes
        processChatSubgraph(data.nodes, data.edges);

        // Render Cypher Logs
        logQueries(data.queries);

        // Refresh stats
        updateStats();

    } catch (error) {
        console.error("Chat error:", error);
        typingIndicator.remove();
        appendMessage("bot", "I apologize, but I encountered an error communicating with the agent server. Please check that the server and Docker container are active.");
    } finally {
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

// Process Subgraph returned by agent
function processChatSubgraph(nodes, edges) {
    if (!nodes || nodes.length === 0) return;

    const nodesToSelect = [];

    // Add any newly discovered or missing nodes to Vis datasets
    nodes.forEach(n => {
        nodesToSelect.push(n.id);
        allNodesMap[n.id] = n;
        
        if (!nodesDataSet.get(n.id)) {
            nodesDataSet.add({
                id: n.id,
                label: n.label,
                group: n.group || "Concept",
                title: n.properties?.description || ""
            });
        }
    });

    edges.forEach(e => {
        if (!edgesDataSet.get(e.id)) {
            edgesDataSet.add({
                id: e.id,
                from: e.from,
                to: e.to,
                label: e.label
            });
        }
    });

    // Select the nodes in graph and pan to them
    network.selectNodes(nodesToSelect);
    
    // Fit camera view to focus on the selected nodes with smooth animation
    if (nodesToSelect.length > 0) {
        // Show details of the first node returned
        showNodeDetails(nodesToSelect[0]);
        
        setTimeout(() => {
            network.fit({
                nodes: nodesToSelect,
                animation: {
                    duration: 1000,
                    easingFunction: "easeInOutQuad"
                }
            });
        }, 300);
    }
}

// Append Chat Messages
function appendMessage(role, content) {
    const msgElement = document.createElement('div');
    msgElement.className = `message ${role === 'user' ? 'user' : 'system'}`;
    
    const avatarHTML = role === 'user' 
        ? '<i class="fa-solid fa-user"></i>' 
        : '<i class="fa-solid fa-robot"></i>';

    // Parse Markdown using marked.js if bot, otherwise render as text
    const processedContent = role === 'user' ? escapeHTML(content) : marked.parse(content);

    msgElement.innerHTML = `
        <div class="message-avatar">
            ${avatarHTML}
        </div>
        <div class="message-content">
            ${processedContent}
        </div>
    `;

    chatMessages.appendChild(msgElement);
    // Scroll chat to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Helper to escape HTML characters for user message
function escapeHTML(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function appendTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'message system';
    indicator.innerHTML = `
        <div class="message-avatar">
            <i class="fa-solid fa-robot"></i>
        </div>
        <div class="message-content typing-bubble">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    chatMessages.appendChild(indicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return indicator;
}

// Render Cypher Queries Logs
function logQueries(queries) {
    if (!queries || queries.length === 0) return;

    // Remove empty message if it exists
    const emptyMsg = queriesContent.querySelector('.empty-queries-msg');
    if (emptyMsg) emptyMsg.remove();

    queries.forEach(q => {
        const codeElement = document.createElement('pre');
        codeElement.className = 'query-log-item';
        codeElement.textContent = `[Cypher Query] ${q}`;
        
        // Prepend so latest queries show on top
        queriesContent.insertBefore(codeElement, queriesContent.firstChild);
    });
}

// Update local stats directly from DataSet lengths
function updateStats() {
    totalNodesVal.textContent = nodesDataSet.length;
    totalEdgesVal.textContent = edgesDataSet.length;
}

// Reset Database action
async function resetDatabase() {
    const confirmReset = confirm("Are you sure you want to reset the database? This will clear the database and restore default seeding data.");
    if (!confirmReset) return;

    showLoading(true, "Resetting Database...");
    try {
        const response = await fetch('/api/seed', { method: 'POST' });
        if (!response.ok) throw new Error("Reset failed");
        
        // Clear local UI components
        chatHistory = [];
        chatMessages.innerHTML = `
            <div class="message system">
                <div class="message-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="message-content">
                    <p>Database cleared and re-seeded successfully! I'm ready for new questions.</p>
                </div>
            </div>
        `;
        queriesContent.innerHTML = '<p class="empty-queries-msg">No queries executed yet. Send a message to start tracing queries.</p>';
        hideNodeDetails();
        
        // Reload full graph
        await loadFullGraph();
    } catch (error) {
        console.error("Error resetting database:", error);
        alert("Failed to reset database.");
    } finally {
        showLoading(false);
    }
}

// Collapsible Trace Panel
function initTracePanel() {
    toggleQueriesBtn.addEventListener('click', () => {
        queriesPanel.classList.toggle('collapsed');
    });
    // Toggle when clicking header too
    document.querySelector('.queries-panel .panel-header').addEventListener('click', (e) => {
        if (e.target !== toggleQueriesBtn && !toggleQueriesBtn.contains(e.target)) {
            queriesPanel.classList.toggle('collapsed');
        }
    });
}

// Event Listeners Initialization
function initEventListeners() {
    chatForm.addEventListener('submit', handleSendMessage);
    btnFullGraph.addEventListener('click', loadFullGraph);
    btnReset.addEventListener('click', resetDatabase);
    closeDetailsBtn.addEventListener('click', hideNodeDetails);
}

// On Window Load
window.addEventListener('load', () => {
    initNetwork();
    initEventListeners();
    initTracePanel();
    loadFullGraph();
});
