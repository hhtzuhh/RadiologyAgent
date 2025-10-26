import React, { useState } from 'react';

const SubAgentCommunication = ({ subAgentData }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!subAgentData) return null;

  const { thinking, toolCalls, toolResponses, artifacts, metadata, status } = subAgentData;

  const agentName = metadata?.adk_app_name || 'Sub-agent';

  return (
    <div className="sub-agent-communication">
      <div className="sub-agent-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="header-left">
          <span className="sub-agent-icon">🤖</span>
          <div className="header-info">
            <span className="agent-name">{agentName}</span>
            <span className="agent-status">{status?.state || 'unknown'}</span>
          </div>
        </div>
        <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>

      {isExpanded && (
        <div className="sub-agent-content">
          {/* Agent Thinking Section */}
          {thinking && thinking.length > 0 && (
            <div className="section">
              <h4>💭 Agent Thinking</h4>
              <div className="thinking-list">
                {thinking.map((thought, idx) => (
                  <div key={idx} className={`thinking-item ${thought.role}`}>
                    <div className="thinking-header">
                      <span className="role-badge">{thought.role}</span>
                    </div>
                    <div className="thinking-text">{thought.text}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tool Calls Section */}
          {toolCalls && toolCalls.length > 0 && (
            <div className="section">
              <h4>🔧 Tool Calls</h4>
              <div className="tool-list">
                {toolCalls.map((call, idx) => (
                  <div key={idx} className="tool-item">
                    <div className="tool-name">{call.toolName}</div>
                    <div className="tool-args">
                      <pre>{JSON.stringify(call.args, null, 2)}</pre>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tool Responses Section */}
          {toolResponses && toolResponses.length > 0 && (
            <div className="section">
              <h4>✓ Tool Results</h4>
              <div className="response-list">
                {toolResponses.map((response, idx) => (
                  <div key={idx} className="response-item">
                    <div className="response-header">
                      <span className="response-name">{response.toolName}</span>
                    </div>
                    <div className="response-content">
                      {renderToolResponse(response)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Artifacts Section */}
          {artifacts && artifacts.length > 0 && (
            <div className="section">
              <h4>📦 Results</h4>
              <div className="artifacts-list">
                {artifacts.map((artifact, idx) => (
                  <div key={idx} className="artifact-item">
                    <div className="artifact-id">Artifact ID: {artifact.artifactId}</div>
                    {artifact.parts && artifact.parts.map((part, partIdx) => (
                      <div key={partIdx} className="artifact-content">
                        {part.kind === 'text' && (
                          <div className="artifact-text">{part.text}</div>
                        )}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata Section */}
          {metadata && (
            <div className="section metadata-section">
              <h4>📊 Statistics</h4>
              <div className="metadata-grid">
                {metadata.adk_usage_metadata && (
                  <>
                    <div className="meta-item">
                      <span className="meta-label">Input Tokens:</span>
                      <span className="meta-value">
                        {metadata.adk_usage_metadata.promptTokenCount}
                      </span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-label">Output Tokens:</span>
                      <span className="meta-value">
                        {metadata.adk_usage_metadata.candidatesTokenCount}
                      </span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-label">Total Tokens:</span>
                      <span className="meta-value">
                        {metadata.adk_usage_metadata.totalTokenCount}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .sub-agent-communication {
          background-color: #2a2a3a;
          border: 2px solid #5a5aaa;
          border-radius: 12px;
          margin: 15px 0;
          overflow: hidden;
        }
        .sub-agent-header {
          padding: 15px 20px;
          background: linear-gradient(135deg, #3a3a5a 0%, #2a2a4a 100%);
          cursor: pointer;
          display: flex;
          justify-content: space-between;
          align-items: center;
          user-select: none;
        }
        .sub-agent-header:hover {
          background: linear-gradient(135deg, #4a4a6a 0%, #3a3a5a 100%);
        }
        .header-left {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .sub-agent-icon {
          font-size: 24px;
        }
        .header-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .agent-name {
          font-weight: bold;
          color: #aaf;
          font-size: 16px;
        }
        .agent-status {
          font-size: 11px;
          color: #8a8;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .expand-icon {
          color: #888;
          font-size: 14px;
        }
        .sub-agent-content {
          padding: 20px;
        }
        .section {
          margin-bottom: 20px;
          padding-bottom: 20px;
          border-bottom: 1px solid #3a3a4a;
        }
        .section:last-child {
          margin-bottom: 0;
          padding-bottom: 0;
          border-bottom: none;
        }
        .section h4 {
          margin: 0 0 12px 0;
          color: #aaa;
          font-size: 14px;
          font-weight: 600;
        }

        /* Thinking List */
        .thinking-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .thinking-item {
          background-color: #333344;
          border-radius: 8px;
          padding: 12px;
          border-left: 3px solid #6a6aaa;
        }
        .thinking-item.user {
          border-left-color: #007aff;
          background-color: #2a3a4a;
        }
        .thinking-item.agent {
          border-left-color: #4ae49e;
          background-color: #2a3a3a;
        }
        .thinking-header {
          margin-bottom: 8px;
        }
        .role-badge {
          display: inline-block;
          padding: 3px 8px;
          background-color: #4a4a6a;
          color: #ddd;
          border-radius: 10px;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
        }
        .thinking-text {
          color: #ddd;
          line-height: 1.5;
          white-space: pre-wrap;
          font-size: 13px;
        }

        /* Tool List */
        .tool-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .tool-item {
          background-color: #2a3f5f;
          border-radius: 8px;
          padding: 12px;
          border-left: 3px solid #4a9eff;
        }
        .tool-name {
          font-family: 'Courier New', monospace;
          color: #4a9eff;
          font-weight: bold;
          margin-bottom: 8px;
          font-size: 14px;
        }
        .tool-args {
          background-color: #1a1a1a;
          padding: 10px;
          border-radius: 4px;
          overflow-x: auto;
        }
        .tool-args pre {
          margin: 0;
          color: #ddd;
          font-size: 12px;
        }

        /* Response List */
        .response-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .response-item {
          background-color: #2a4f3f;
          border-radius: 8px;
          padding: 12px;
          border-left: 3px solid #4ae49e;
        }
        .response-header {
          margin-bottom: 8px;
        }
        .response-name {
          font-family: 'Courier New', monospace;
          color: #4ae49e;
          font-weight: bold;
          font-size: 14px;
        }
        .response-content {
          background-color: #1a1a1a;
          padding: 10px;
          border-radius: 4px;
          max-height: 300px;
          overflow-y: auto;
        }
        .response-json {
          margin: 0;
          color: #ddd;
          font-size: 12px;
        }
        .response-summary {
          color: #ddd;
          font-size: 13px;
          line-height: 1.5;
        }

        /* Artifacts List */
        .artifacts-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .artifact-item {
          background-color: #3a3a4a;
          border-radius: 8px;
          padding: 12px;
        }
        .artifact-id {
          font-size: 11px;
          color: #888;
          margin-bottom: 8px;
          font-family: monospace;
        }
        .artifact-text {
          color: #ddd;
          line-height: 1.5;
          white-space: pre-wrap;
          font-size: 13px;
        }

        /* Metadata Section */
        .metadata-section {
          background-color: #2a2a2a;
          border-radius: 8px;
          padding: 15px;
        }
        .metadata-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 12px;
        }
        .meta-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .meta-label {
          font-size: 11px;
          color: #888;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .meta-value {
          font-size: 16px;
          color: #4ae49e;
          font-weight: bold;
          font-family: monospace;
        }
      `}</style>
    </div>
  );
};

// Helper function to render tool responses
function renderToolResponse(response) {
  const { toolName, response: responseData } = response;

  // Special handling for search results
  if (toolName === 'search_radiology_reports_hybrid') {
    const resultCount = responseData.results?.length || 0;
    return (
      <div className="response-summary">
        <div>✓ Found {resultCount} reports</div>
        <div>Strategy: {responseData.search_metadata?.strategy || responseData.strategy}</div>
        {responseData.search_metadata?.score_range && (
          <div>
            Score range: {responseData.search_metadata.score_range.min.toFixed(3)} - {responseData.search_metadata.score_range.max.toFixed(3)}
          </div>
        )}
      </div>
    );
  }

  // Default: show JSON
  return (
    <pre className="response-json">{JSON.stringify(responseData, null, 2)}</pre>
  );
}

export default SubAgentCommunication;
