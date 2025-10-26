/**
 * XRayImageDisplay Component
 *
 * Displays X-ray images from search and vision results.
 * Shows image, patient ID, CheXbert labels, and similarity scores.
 */

import React, { useState } from 'react';

interface ChexbertLabels {
  [key: string]: number | null;
}

interface XRayCase {
  report_id: string;
  patient_id?: string;
  image_url?: string;
  chexbert_labels?: ChexbertLabels;
  similarity_score?: number;
  report_snippet?: string;
}

interface XRayImageDisplayProps {
  cases: XRayCase[];
  title?: string;
}

export const XRayImageDisplay: React.FC<XRayImageDisplayProps> = ({
  cases,
  title = "X-Ray Results"
}) => {
  const [selectedCase, setSelectedCase] = useState<XRayCase | null>(null);

  const getPositiveLabels = (labels?: ChexbertLabels) => {
    if (!labels) return [];
    return Object.entries(labels)
      .filter(([_, value]) => value === 1.0)
      .map(([label]) => label);
  };

  const getSimilarityColor = (score?: number) => {
    if (!score) return 'gray';
    if (score > 0.8) return 'green';
    if (score > 0.6) return 'blue';
    return 'yellow';
  };

  return (
    <div className="xray-display">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cases.map((xrayCase, index) => {
          const positiveLabels = getPositiveLabels(xrayCase.chexbert_labels);

          return (
            <div
              key={index}
              className="border rounded-lg overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => setSelectedCase(xrayCase)}
            >
              {/* X-Ray Image */}
              <div className="relative bg-black aspect-square">
                {xrayCase.image_url ? (
                  <img
                    src={xrayCase.image_url}
                    alt={`X-Ray ${xrayCase.patient_id || index}`}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">
                    <span>No Image Available</span>
                  </div>
                )}

                {/* Similarity Score Badge */}
                {xrayCase.similarity_score && (
                  <div className={`
                    absolute top-2 right-2 px-3 py-1 rounded-full
                    bg-${getSimilarityColor(xrayCase.similarity_score)}-500
                    text-white text-sm font-semibold
                  `}>
                    {(xrayCase.similarity_score * 100).toFixed(0)}% Match
                  </div>
                )}
              </div>

              {/* Metadata */}
              <div className="p-4">
                <div className="mb-2">
                  <p className="text-sm text-gray-600">
                    Patient: <span className="font-semibold">{xrayCase.patient_id || 'Unknown'}</span>
                  </p>
                  <p className="text-xs text-gray-500 truncate" title={xrayCase.report_id}>
                    {xrayCase.report_id}
                  </p>
                </div>

                {/* CheXbert Labels */}
                {positiveLabels.length > 0 && (
                  <div className="mb-2">
                    <p className="text-xs text-gray-600 mb-1">Findings:</p>
                    <div className="flex flex-wrap gap-1">
                      {positiveLabels.slice(0, 3).map((label) => (
                        <span
                          key={label}
                          className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded"
                        >
                          {label}
                        </span>
                      ))}
                      {positiveLabels.length > 3 && (
                        <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                          +{positiveLabels.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Report Snippet */}
                {xrayCase.report_snippet && (
                  <p className="text-xs text-gray-600 line-clamp-2">
                    {xrayCase.report_snippet}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal for selected case */}
      {selectedCase && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedCase(null)}
        >
          <div
            className="bg-white rounded-lg max-w-4xl w-full max-h-screen overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-xl font-semibold">
                  Patient: {selectedCase.patient_id}
                </h3>
                <button
                  onClick={() => setSelectedCase(null)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Full Image */}
                <div className="bg-black rounded-lg aspect-square">
                  {selectedCase.image_url && (
                    <img
                      src={selectedCase.image_url}
                      alt={`X-Ray ${selectedCase.patient_id}`}
                      className="w-full h-full object-contain"
                    />
                  )}
                </div>

                {/* Details */}
                <div>
                  <h4 className="font-semibold mb-2">Report ID:</h4>
                  <p className="text-sm text-gray-600 mb-4 break-all">
                    {selectedCase.report_id}
                  </p>

                  {selectedCase.chexbert_labels && (
                    <>
                      <h4 className="font-semibold mb-2">CheXbert Labels:</h4>
                      <div className="space-y-1 mb-4">
                        {Object.entries(selectedCase.chexbert_labels).map(([label, value]) => (
                          <div key={label} className="flex justify-between text-sm">
                            <span>{label}:</span>
                            <span className={`
                              font-semibold
                              ${value === 1.0 ? 'text-red-600' : ''}
                              ${value === 0.0 ? 'text-green-600' : ''}
                              ${value === -1.0 ? 'text-yellow-600' : ''}
                              ${value === null ? 'text-gray-400' : ''}
                            `}>
                              {value === 1.0 ? 'Positive' : ''}
                              {value === 0.0 ? 'Negative' : ''}
                              {value === -1.0 ? 'Uncertain' : ''}
                              {value === null ? 'Not Mentioned' : ''}
                            </span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}

                  {selectedCase.report_snippet && (
                    <>
                      <h4 className="font-semibold mb-2">Report Excerpt:</h4>
                      <p className="text-sm text-gray-700">
                        {selectedCase.report_snippet}
                      </p>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
