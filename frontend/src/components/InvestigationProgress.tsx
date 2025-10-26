// frontend/src/components/InvestigationProgress.tsx
import { useState, useEffect } from 'react';

interface Step {
  step: number;
  agent: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  started_at: number | null;
  completed_at: number | null;
  error: string | null;
}

interface ProgressData {
  investigation_plan: Step[];
  current_step: number;
  total_steps: number;
  plan_status: string;
}

function InvestigationProgress({ sessionId }: { sessionId: string }) {
  const [progress, setProgress] = useState<ProgressData | null>(null);

  useEffect(() => {
    // Poll every 500ms while investigation is in progress
    const interval = setInterval(async () => {
      const response = await fetch(`/api/sessions/${sessionId}/progress`);
      const data = await response.json();
      setProgress(data);

      // Stop polling if completed
      if (data.plan_status === 'completed') {
        clearInterval(interval);
      }
    }, 500);

    return () => clearInterval(interval);
  }, [sessionId]);

  if (!progress || !progress.investigation_plan) {
    return <div>No investigation in progress</div>;
  }

  return (
    <div className="investigation-progress">
      <h3>Investigation Progress ({progress.current_step}/{progress.total_steps})</h3>

      <div className="steps">
        {progress.investigation_plan.map((step) => (
          <div key={step.step} className={`step step-${step.status}`}>
            <div className="step-header">
              <span className="step-icon">
                {step.status === 'completed' && '✅'}
                {step.status === 'in_progress' && '⏳'}
                {step.status === 'pending' && '⏸️'}
                {step.status === 'failed' && '❌'}
              </span>
              <span className="step-number">Step {step.step}</span>
              <span className="step-agent">{step.agent}</span>
            </div>

            <div className="step-description">{step.description}</div>

            {step.completed_at && step.started_at && (
              <div className="step-duration">
                Duration: {(step.completed_at - step.started_at).toFixed(2)}s
              </div>
            )}

            {step.error && (
              <div className="step-error">Error: {step.error}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
