import React, { useState } from 'react';

const ToolCall = ({ toolName, args, toolId }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="tool-call">
      <div className="tool-header" onClick={() => setIsExpanded(!isExpanded)}>
        <span className="tool-icon">🔧</span>
        <span className="tool-name">{toolName}</span>
        <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>
      {isExpanded && (
        <div className="tool-details">
          <div className="tool-id">ID: {toolId}</div>
          <div className="tool-args">
            <strong>Parameters:</strong>
            <pre>{JSON.stringify(args, null, 2)}</pre>
          </div>
        </div>
      )}
      <style jsx>{`
        .tool-call {
          background-color: #2a3f5f;
          border-left: 3px solid #4a9eff;
          border-radius: 6px;
          margin: 8px 0;
          overflow: hidden;
        }
        .tool-header {
          padding: 10px 15px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 10px;
          user-select: none;
        }
        .tool-header:hover {
          background-color: #344f6f;
        }
        .tool-icon {
          font-size: 18px;
        }
        .tool-name {
          font-family: 'Courier New', monospace;
          color: #4a9eff;
          font-weight: bold;
          flex-grow: 1;
        }
        .expand-icon {
          color: #aaa;
          font-size: 12px;
        }
        .tool-details {
          padding: 0 15px 15px 15px;
          border-top: 1px solid #3a4f6f;
        }
        .tool-id {
          font-size: 11px;
          color: #888;
          margin-bottom: 8px;
          font-family: monospace;
        }
        .tool-args {
          margin-top: 8px;
        }
        .tool-args strong {
          color: #aaa;
          font-size: 12px;
        }
        .tool-args pre {
          background-color: #1a1a1a;
          padding: 10px;
          border-radius: 4px;
          overflow-x: auto;
          font-size: 12px;
          color: #ddd;
          margin-top: 5px;
        }
      `}</style>
    </div>
  );
};

export default ToolCall;
