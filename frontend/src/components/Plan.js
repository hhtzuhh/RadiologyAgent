import React from 'react';

const Plan = ({ plan }) => {
  if (!plan || plan.length === 0) {
    return null;
  }

  return (
    <div className="plan-container">
      <h4>Investigation Plan:</h4>
      <ol>
        {plan.map((step) => (
          <li key={step.step}>
            <span>{step.agent}:</span> {step.description}
          </li>
        ))}
      </ol>
      <style jsx>{`
        .plan-container {
          background-color: #2a2a2a;
          border: 1px solid #444;
          border-radius: 8px;
          padding: 15px;
          margin-bottom: 15px;
        }
        h4 {
          margin-bottom: 10px;
          color: #aaa;
        }
        ol {
          padding-left: 20px;
        }
        li {
          margin-bottom: 8px;
          color: #ccc;
        }
        span {
          font-weight: bold;
          color: #ddd;
        }
      `}</style>
    </div>
  );
};

export default Plan;
