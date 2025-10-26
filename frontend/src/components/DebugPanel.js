import React, { useState } from 'react';

const DebugPanel = ({ taskMetadata, subAgentData, searchResults, messages }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="debug-panel">
      <div className="debug-header" onClick={() => setIsExpanded(!isExpanded)}>
        <span>🔍 Debug Panel</span>
        <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>

      {isExpanded && (
        <div className="debug-content">
          <div className="debug-section">
            <h4>Task Metadata</h4>
            <div className="debug-info">
              <div>Agent: {taskMetadata?.adk_app_name || 'N/A'}</div>
              <div>Has custom metadata: {taskMetadata?.adk_custom_metadata ? 'Yes' : 'No'}</div>
              {taskMetadata?.adk_custom_metadata && (
                <div>Type: {typeof taskMetadata.adk_custom_metadata}</div>
              )}
            </div>
          </div>

          <div className="debug-section">
            <h4>Sub-Agent Data</h4>
            <div className="debug-info">
              {subAgentData ? (
                <>
                  <div>✓ Sub-agent data found</div>
                  <div>Thinking items: {subAgentData.thinking?.length || 0}</div>
                  <div>Tool calls: {subAgentData.toolCalls?.length || 0}</div>
                  <div>Tool responses: {subAgentData.toolResponses?.length || 0}</div>
                  <div>Search results: {subAgentData.searchResults?.length || 0}</div>
                  <div>Artifacts: {subAgentData.artifacts?.length || 0}</div>
                </>
              ) : (
                <div>✗ No sub-agent data</div>
              )}
            </div>
          </div>

          <div className="debug-section">
            <h4>Search Results</h4>
            <div className="debug-info">
              <div>Total search results: {searchResults?.length || 0}</div>
              {searchResults && searchResults.map((sr, idx) => (
                <div key={idx} className="search-result-debug">
                  Result set {idx + 1}: {sr.results?.length || 0} reports
                  (Query: {sr.metadata?.query || 'N/A'})
                </div>
              ))}
            </div>
          </div>

          <div className="debug-section">
            <h4>Messages</h4>
            <div className="debug-info">
              <div>Total messages: {messages?.length || 0}</div>
              {messages && messages.map((msg, idx) => (
                <div key={idx} className="message-debug">
                  Message {idx + 1}: {msg.role} - {msg.parts?.length || 0} parts
                </div>
              ))}
            </div>
          </div>

          <div className="debug-section">
            <h4>Console Logs</h4>
            <div className="debug-info">
              Check browser console (F12) for detailed logs
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .debug-panel {
          background-color: #1a1a2e;
          border: 2px solid #ff6b6b;
          border-radius: 8px;
          margin: 15px 0;
          font-family: monospace;
          font-size: 12px;
        }
        .debug-header {
          padding: 12px 15px;
          background-color: #2a2a3e;
          cursor: pointer;
          display: flex;
          justify-content: space-between;
          align-items: center;
          user-select: none;
          color: #ff6b6b;
          font-weight: bold;
        }
        .debug-header:hover {
          background-color: #3a3a4e;
        }
        .expand-icon {
          color: #888;
        }
        .debug-content {
          padding: 15px;
        }
        .debug-section {
          margin-bottom: 15px;
          padding-bottom: 15px;
          border-bottom: 1px solid #3a3a4e;
        }
        .debug-section:last-child {
          margin-bottom: 0;
          padding-bottom: 0;
          border-bottom: none;
        }
        .debug-section h4 {
          margin: 0 0 10px 0;
          color: #ff6b6b;
          font-size: 13px;
        }
        .debug-info {
          color: #ccc;
          line-height: 1.6;
        }
        .debug-info > div {
          margin-bottom: 4px;
        }
        .search-result-debug,
        .message-debug {
          padding-left: 15px;
          color: #aaa;
          font-size: 11px;
        }
      `}</style>
    </div>
  );
};

export default DebugPanel;
