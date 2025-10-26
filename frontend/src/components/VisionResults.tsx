'use client';

import { useState } from 'react';
import { SimilarCase } from '@/types/events';
import ReportModal from './ReportModal';

interface VisionResultsProps {
  cases: SimilarCase[];
}

export default function VisionResults({ cases }: VisionResultsProps) {
  const [selectedCase, setSelectedCase] = useState<SimilarCase | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  if (cases.length === 0) return null;

  const openModal = (similarCase: SimilarCase) => {
    setSelectedCase(similarCase);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedCase(null);
  };

  const truncateText = (text: string, maxLength: number) => {
    if (text.length <= maxLength) {
      return text;
    }
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div className="vision-results">
      <h3>Similar Cases ({cases.length} found)</h3>
      <div className="results-grid">
        {cases.map((similar, index) => (
          <div key={index} className="result-card" onClick={() => openModal(similar)}>
            <div className="result-header">
              <span className="patient-id">{similar.patient_id}</span>
              <span className="similarity">
                Similarity: {(similar.similarity_score * 100).toFixed(1)}%
              </span>
            </div>
            {similar.image_url && (
              <div className="image-preview">
                <img src={similar.image_url} alt="X-ray preview" />
              </div>
            )}
            <div className="result-text">
              {truncateText(similar.report_text, 300)}
            </div>
          </div>
        ))}
      </div>
      <ReportModal
        isOpen={isModalOpen}
        report={selectedCase ? {
          title: `Similar Case for ${selectedCase.patient_id}`,
          image: selectedCase.image_url,
          fullText: selectedCase.report_text,
        } : null}
        onClose={closeModal}
      />
    </div>
  );
}
