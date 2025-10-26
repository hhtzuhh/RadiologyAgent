'use client';

import { InvestigationStep } from '@/types/events';

interface InvestigationPlanProps {
  plan: InvestigationStep[];
  completedSteps: Set<number>;
}

export default function InvestigationPlan({
  plan,
  completedSteps,
}: InvestigationPlanProps) {
  if (!plan || plan.length === 0) {
    return null;
  }

  return (
    <div className="investigation-plan">
      <h2>Investigation Plan</h2>
      <div className="steps">
        {plan.map((step) => (
          <div
            key={step.step}
            className={`step ${completedSteps.has(step.step) ? 'completed' : ''}`}
          >
            <div className="step-number">Step {step.step}</div>
            <div className="step-content">
              <div className="step-agent">{step.agent}</div>
              <div className="step-description">{step.description}</div>
            </div>
            {completedSteps.has(step.step) && (
              <div className="checkmark">✓</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}