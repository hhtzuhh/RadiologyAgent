import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';

const ReportModal = ({ report, isOpen, onClose }) => {
  const [isBrowser, setIsBrowser] = useState(false);

  useEffect(() => {
    setIsBrowser(true);
  }, []);

  if (!isOpen || !report) {
    return null;
  }

  const modalContent = (
    <div className="modal">
      <div className="modal-content">
        <div className="modal-header">
          <h2 className="modal-title">Report for {report.patient_id}</h2>
          <button
            onClick={onClose}
            className="close-button"
          >
            &times;
          </button>
        </div>
        <div className="modal-body">
          <div className="modal-layout">
            {/* Left side - Image */}
            <div className="modal-image-section">
              {report.image_url && (
                <img
                  src={report.image_url}
                  alt="X-ray"
                />
              )}
            </div>

            {/* Right side - Text content */}
            <div className="modal-text-section">
              {report.score !== undefined && (
                <div className="modal-score">
                  <span className="score">Score: {report.score.toFixed(2)}</span>
                </div>
              )}
              {report.chexbert_labels && (
                <div className="labels">
                  {Object.entries(report.chexbert_labels)
                    .filter(([_, value]) => value === 1)
                    .map(([key]) => (
                      <span key={key} className="label">{key}</span>
                    ))}
                </div>
              )}
              <div className="report-text-content">
                {report.report_text}
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  if (isBrowser) {
    const modalRoot = document.getElementById('modal-root');
    return modalRoot ? ReactDOM.createPortal(modalContent, modalRoot) : null;
  } else {
    return null;
  }
};

export default ReportModal;