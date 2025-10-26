import React, { useState } from 'react';

const AgentFlowTimeline = ({ messages }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!messages || messages.length === 0) return null;

  const getAgentFromMessage = (message) => {
    // Try to determine which agent sent this message
    // This would need to be extracted from metadata in a real implementation
    return message.role === 'user' ? 'User' : 'Orchestrator';
  };

  const renderFlowItem = (message, index) => {
    const agent = getAgentFromMessage(message);

    return (
      <div key={message.id} className="flow-item">
        <div className="flow-connector">
          {index > 0 && <div className="connector-line"></div>}
          <div className={`flow-dot ${message.role}`}></div>
          {index < messages.length - 1 && <div className="connector-line"></div>}
        </div>

        <div className="flow-content">
          <div className="flow-header">
            <span className="agent-name">{agent}</span>
            <span className="message-time">Step {index + 1}</span>
          </div>

          <div className="flow-details">
            {message.parts.map((part, partIdx) => {
              if (part.type === 'text') {
                return (
                  <div key={partIdx} className="flow-text">
                    💭 {part.content.substring(0, 100)}
                    {part.content.length > 100 && '...'}
                  </div>
                );
              } else if (part.type === 'tool_call') {
                return (
                  <div key={partIdx} className="flow-tool-call">
                    🔧 Called: <strong>{part.toolName}</strong>
                  </div>
                );
              } else if (part.type === 'tool_response') {
                return (
                  <div key={partIdx} className="flow-tool-response">
                    ✓ Response from: <strong>{part.toolName}</strong>
                  </div>
                );
              }
              return null;
            })}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="agent-flow-timeline">
      <div className="timeline-header" onClick={() => setIsExpanded(!isExpanded)}>
        <h4>🔄 Agent Communication Flow</h4>
        <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>

      {isExpanded && (
        <div className="timeline-content">
          {messages.map((message, index) => renderFlowItem(message, index))}
        </div>
      )}

      <style jsx>{`
        .agent-flow-timeline {
          background-color: #2a2a2a;
          border: 1px solid #444;
          border-radius: 8px;
          margin: 15px 0;
          overflow: hidden;
        }
        .timeline-header {
          padding: 15px;
          cursor: pointer;
          display: flex;
          justify-content: space-between;
          align-items: center;
          user-select: none;
          background-color: #333;
        }
        .timeline-header:hover {
          background-color: #3a3a3a;
        }
        .timeline-header h4 {
          margin: 0;
          color: #ddd;
          font-size: 15px;
        }
        .expand-icon {
          color: #888;
          font-size: 12px;
        }
        .timeline-content {
          padding: 20px;
          max-height: 600px;
          overflow-y: auto;
        }
        .flow-item {
          display: flex;
          gap: 15px;
          margin-bottom: 20px;
        }
        .flow-item:last-child {
          margin-bottom: 0;
        }
        .flow-connector {
          display: flex;
          flex-direction: column;
          align-items: center;
          width: 30px;
          flex-shrink: 0;
        }
        .connector-line {
          width: 2px;
          flex: 1;
          background-color: #444;
          min-height: 20px;
        }
        .flow-dot {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          flex-shrink: 0;
          margin: 5px 0;
        }
        .flow-dot.user {
          background-color: #007aff;
          box-shadow: 0 0 8px rgba(0, 122, 255, 0.5);
        }
        .flow-dot.agent {
          background-color: #4ae49e;
          box-shadow: 0 0 8px rgba(74, 228, 158, 0.5);
        }
        .flow-content {
          flex: 1;
          background-color: #333;
          border-radius: 8px;
          padding: 12px;
          border: 1px solid #444;
        }
        .flow-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
        }
        .agent-name {
          font-weight: bold;
          color: #4ae49e;
          font-size: 14px;
        }
        .message-time {
          font-size: 11px;
          color: #888;
        }
        .flow-details {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .flow-text {
          font-size: 13px;
          color: #ccc;
          line-height: 1.4;
        }
        .flow-tool-call {
          font-size: 13px;
          color: #4a9eff;
          padding: 6px 10px;
          background-color: #2a3f5f;
          border-radius: 4px;
        }
        .flow-tool-call strong {
          color: #6ab4ff;
        }
        .flow-tool-response {
          font-size: 13px;
          color: #4ae49e;
          padding: 6px 10px;
          background-color: #2a4f3f;
          border-radius: 4px;
        }
        .flow-tool-response strong {
          color: #6af4be;
        }
      `}</style>
    </div>
  );
};

export default AgentFlowTimeline;
