import React, { useState } from 'react';

const SearchResults = ({ searchData }) => {
  const [expandedReportId, setExpandedReportId] = useState(null);

  console.log('SearchResults component received searchData:', searchData);
  console.log('Has results?', !!searchData?.results);
  console.log('Results length:', searchData?.results?.length);

  if (!searchData || !searchData.results || searchData.results.length === 0) {
    console.log('SearchResults: returning null (no data)');
    return null;
  }

  const { metadata, results } = searchData;
  console.log('SearchResults: rendering with', results.length, 'reports');

  const toggleReport = (reportId) => {
    setExpandedReportId(expandedReportId === reportId ? null : reportId);
  };

  const renderChexbertLabels = (labels) => {
    if (!labels) return null;

    const positiveLabels = Object.entries(labels)
      .filter(([_, value]) => value === 1.0)
      .map(([key, _]) => key);

    if (positiveLabels.length === 0) return <span style={{ color: '#666', fontStyle: 'italic', fontSize: '12px' }}>No positive findings</span>;

    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {positiveLabels.map(label => (
          <span key={label} style={{ backgroundColor: '#4a5f7a', color: '#fff', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: '500' }}>{label}</span>
        ))}
      </div>
    );
  };

  return (
    <div className="search-results" style={{ backgroundColor: '#ff0000', padding: '20px', margin: '20px 0' }}>
      <div style={{ color: 'white', fontSize: '24px', fontWeight: 'bold' }}>
        TEST: Search Results Component is Rendering!
      </div>
      <div className="results-header" style={{ backgroundColor: '#333344', padding: '15px', color: 'white' }}>
        <h4 style={{ margin: '0 0 10px 0' }}>📋 Search Results</h4>
        <div className="metadata" style={{ display: 'flex', flexWrap: 'wrap', gap: '15px' }}>
          <div className="meta-item" style={{ color: '#ddd' }}>
            <strong>Query:</strong> {metadata.query}
          </div>
          <div className="meta-item" style={{ color: '#ddd' }}>
            <strong>Strategy:</strong> {metadata.strategy}
          </div>
          <div className="meta-item" style={{ color: '#ddd' }}>
            <strong>Results:</strong> {metadata.resultCount}
          </div>
          {metadata.scoreRange && (
            <div className="meta-item" style={{ color: '#ddd' }}>
              <strong>Score Range:</strong> {metadata.scoreRange.min.toFixed(3)} - {metadata.scoreRange.max.toFixed(3)}
              (avg: {metadata.scoreRange.avg.toFixed(3)})
            </div>
          )}
        </div>
      </div>

      <div className="results-list" style={{ maxHeight: '600px', overflowY: 'auto' }}>
        {results.map((result, idx) => (
          <div key={result.report_id || idx} className="result-item" style={{ borderBottom: '1px solid #3a3a4a', backgroundColor: '#2a2a2a', color: 'white' }}>
            <div
              className="result-header"
              onClick={() => toggleReport(result.report_id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '15px',
                cursor: 'pointer',
                gap: '15px'
              }}
            >
              <div className="result-rank" style={{ fontSize: '18px', fontWeight: 'bold', color: '#888', minWidth: '40px' }}>#{idx + 1}</div>
              <div className="result-info" style={{ flexGrow: 1 }}>
                <div className="result-id" style={{ fontFamily: 'monospace', fontSize: '12px', color: '#4a9eff', marginBottom: '3px' }}>{result.report_id}</div>
                <div className="result-patient" style={{ fontSize: '11px', color: '#888' }}>Patient: {result.patient_id}</div>
              </div>
              <div className="result-score" style={{ fontSize: '14px', color: '#aaa' }}>
                Score: <strong style={{ color: '#4ae49e', fontFamily: 'monospace' }}>{result.score.toFixed(4)}</strong>
              </div>
              <span className="expand-icon" style={{ color: '#666', fontSize: '12px' }}>
                {expandedReportId === result.report_id ? '▼' : '▶'}
              </span>
            </div>

            {expandedReportId === result.report_id && (
              <div style={{ padding: '15px', backgroundColor: '#25252f', borderTop: '1px solid #3a3a4a' }}>
                <div style={{ marginBottom: '15px' }}>
                  <h5 style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#aaa', fontWeight: '600' }}>CheXbert Labels:</h5>
                  {renderChexbertLabels(result.chexbert_labels)}
                </div>

                {result.radgraph_findings && result.radgraph_findings.length > 0 && (
                  <div style={{ marginBottom: '15px' }}>
                    <h5 style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#aaa', fontWeight: '600' }}>RadGraph Findings:</h5>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {result.radgraph_findings.slice(0, 10).map((finding, i) => (
                        <span key={i} style={{ backgroundColor: '#3a3a4a', color: '#ccc', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontFamily: 'monospace' }}>{finding}</span>
                      ))}
                      {result.radgraph_findings.length > 10 && (
                        <span style={{ color: '#888', fontStyle: 'italic', fontSize: '11px', padding: '4px 8px' }}>+{result.radgraph_findings.length - 10} more</span>
                      )}
                    </div>
                  </div>
                )}

                {result.radgraph_impression && result.radgraph_impression.length > 0 && (
                  <div style={{ marginBottom: '15px' }}>
                    <h5 style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#aaa', fontWeight: '600' }}>RadGraph Impression:</h5>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {result.radgraph_impression.map((imp, i) => (
                        <span key={i} style={{ backgroundColor: '#3a3a4a', color: '#ccc', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontFamily: 'monospace' }}>{imp}</span>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ marginBottom: '0' }}>
                  <h5 style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#aaa', fontWeight: '600' }}>Full Report:</h5>
                  <div style={{ backgroundColor: '#1a1a1f', padding: '12px', borderRadius: '6px', fontFamily: 'monospace', fontSize: '12px', color: '#ddd', whiteSpace: 'pre-wrap', lineHeight: '1.5', maxHeight: '300px', overflowY: 'auto' }}>{result.report_text}</div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default SearchResults;
