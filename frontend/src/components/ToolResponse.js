import React, { useState } from 'react';

const ToolResponse = ({ toolName, response, toolId }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Helper to render response based on type
  const renderResponse = () => {
    if (!response) return <div className="no-response">No response data</div>;

    // If it's the plan display tool
    if (toolName === 'display_investigation_plan') {
      return (
        <div className="plan-response">
          <div className="status">Status: {response.status}</div>
          {response.plan && (
            <ol className="plan-list">
              {response.plan.map((step) => (
                <li key={step.step}>
                  <strong>{step.agent}:</strong> {step.description}
                </li>
              ))}
            </ol>
          )}
        </div>
      );
    }

    // If it's a search result (handled separately by SearchResults component)
    if (toolName === 'search_radiology_reports_hybrid') {
      return (
        <div className="search-summary">
          <div>Query: <strong>{response.query || response.search_metadata?.query}</strong></div>
          <div>Results: <strong>{response.results?.length || 0}</strong></div>
          <div className="note">📊 See detailed results below</div>
        </div>
      );
    }

    // For transfer_to_agent
    if (toolName === 'transfer_to_agent') {
      return (
        <div className="transfer-response">
          <div>✓ Control transferred successfully</div>
        </div>
      );
    }

    // Default: show JSON
    return <pre className="json-response">{JSON.stringify(response, null, 2)}</pre>;
  };

  return (
    <div className="tool-response">
      <div className="response-header" onClick={() => setIsExpanded(!isExpanded)}>
        <span className="response-icon">✓</span>
        <span className="response-name">{toolName} response</span>
        <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>
      {isExpanded && (
        <div className="response-details">
          <div className="tool-id">ID: {toolId}</div>
          <div className="response-content">
            {renderResponse()}
          </div>
        </div>
      )}
      <style jsx>{`
        .tool-response {
          background-color: #2a4f3f;
          border-left: 3px solid #4ae49e;
          border-radius: 6px;
          margin: 8px 0;
          overflow: hidden;
        }
        .response-header {
          padding: 10px 15px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 10px;
          user-select: none;
        }
        .response-header:hover {
          background-color: #345f4f;
        }
        .response-icon {
          font-size: 18px;
          color: #4ae49e;
        }
        .response-name {
          font-family: 'Courier New', monospace;
          color: #4ae49e;
          font-weight: bold;
          flex-grow: 1;
        }
        .expand-icon {
          color: #aaa;
          font-size: 12px;
        }
        .response-details {
          padding: 0 15px 15px 15px;
          border-top: 1px solid #3a5f4f;
        }
        .tool-id {
          font-size: 11px;
          color: #888;
          margin-bottom: 8px;
          font-family: monospace;
        }
        .response-content {
          margin-top: 8px;
        }
        .json-response {
          background-color: #1a1a1a;
          padding: 10px;
          border-radius: 4px;
          overflow-x: auto;
          font-size: 12px;
          color: #ddd;
        }
        .no-response {
          color: #888;
          font-style: italic;
          padding: 10px;
        }
        .plan-response .status {
          color: #4ae49e;
          margin-bottom: 10px;
          font-weight: bold;
        }
        .plan-list {
          padding-left: 20px;
          margin-top: 10px;
        }
        .plan-list li {
          margin-bottom: 8px;
          color: #ddd;
        }
        .plan-list strong {
          color: #4ae49e;
        }
        .search-summary {
          padding: 10px;
          background-color: #1a2a2a;
          border-radius: 4px;
        }
        .search-summary > div {
          margin-bottom: 5px;
          color: #ccc;
        }
        .search-summary strong {
          color: #4ae49e;
        }
        .search-summary .note {
          margin-top: 10px;
          padding-top: 10px;
          border-top: 1px solid #3a4a4a;
          color: #888;
          font-style: italic;
        }
        .transfer-response {
          padding: 10px;
          color: #4ae49e;
        }
      `}</style>
    </div>
  );
};

export default ToolResponse;
