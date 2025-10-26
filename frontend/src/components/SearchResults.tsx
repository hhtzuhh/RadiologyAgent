'use client';

import { Report } from '@/types/events';

interface SearchResultsProps {
  reports: Report[];
  count: number;
  searchMetadata: any;
  onReportClick: (report: Report) => void;
}

export default function SearchResults({ reports, count, searchMetadata, onReportClick }: SearchResultsProps) {
  if (reports.length === 0) return null;

  const truncateText = (text: string, maxLength: number) => {
    if (text.length <= maxLength) {
      return text;
    }
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div className="search-results">
      <h3>Search Results ({count} reports found)</h3>
      {searchMetadata && (
        <div className="search-metadata">
          <p><strong>Query:</strong> {searchMetadata.query}</p>
          <p><strong>Strategy:</strong> {searchMetadata.strategy}</p>
          {searchMetadata.score_range && (
            <p>
              <strong>Score Range:</strong> Min: {searchMetadata.score_range.min.toFixed(2)}, Max: {searchMetadata.score_range.max.toFixed(2)}, Avg: {searchMetadata.score_range.avg.toFixed(2)}
            </p>
          )}
          {searchMetadata.parameters && (
            <p>
              <strong>Parameters:</strong> Top K Stage 1: {searchMetadata.parameters.top_k_stage1}, Top N Final: {searchMetadata.parameters.top_n_final}
            </p>
          )}
        </div>
      )}
      <div className="results-grid">
        {reports.map((report, index) => (
          <div key={index} className="result-card" onClick={() => onReportClick(report)}>
            <div className="result-header">
              <span className="patient-id">{report.patient_id}</span>
              <span className="score">Score: {report.score.toFixed(2)}</span>
            </div>
            {report.image_url && (
              <div className="image-preview">
                <img src={report.image_url} alt="X-ray preview" />
              </div>
            )}
            <div className="result-text">
              {truncateText(report.report_text, 300)}
            </div>
            {report.chexbert_labels && (
              <div className="labels">
                {Object.entries(report.chexbert_labels)
                  .filter(([_, value]) => value === 1)
                  .map(([key]) => (
                    <span key={key} className="label">{key}</span>
                  ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
