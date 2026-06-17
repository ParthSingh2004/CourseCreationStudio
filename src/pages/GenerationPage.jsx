import { useEffect, useState } from 'react';
import { IconCheck, IconArrowLeft } from '../icons';

const API_BASE = import.meta.env.VITE_API_BASE || 
  (window.location.origin.includes('5173') ? 'http://localhost:8000/api/v1' : `${window.location.origin}/api/v1`);

const STEP_METADATA = {
  design: { label: 'Designing Curriculum', desc: 'Generating course outline and learning objectives.' },
  write: { label: 'Writing Content', desc: 'Generating lesson segments, quizzes, and flashcards.' },
  audio: { label: 'Synthesizing Audio', desc: 'Generating natural voiceovers.' },
  slides: { label: 'Building Slides', desc: 'Creating PPTX slide deck.' },
  pdf: { label: 'Exporting PDFs', desc: 'Creating Quiz and Summary PDFs.' }
};

const spinnerStyle = `
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
`;

const Spinner = () => (
  <svg style={{
    animation: 'spin 1s linear infinite',
    width: '18px',
    height: '18px',
    color: 'var(--brand, #3b82f6)'
  }} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
    <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
    <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
  </svg>
);

export default function GenerationPage({ jobId, onComplete, onBack }) {
  const [steps, setSteps] = useState([
    { id: 'design', label: 'Designing Curriculum', desc: 'Generating course outline and learning objectives.' }
  ]);
  const [activeStepId, setActiveStepId] = useState('design');
  const [completedSteps, setCompletedSteps] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    if (!jobId) return;
    
    const eventSource = new EventSource(`${API_BASE}/generate/stream/${jobId}`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.step === 'init') {
        const activeSteps = data.steps.map(id => ({
          id,
          label: STEP_METADATA[id]?.label || id,
          desc: STEP_METADATA[id]?.desc || ''
        }));
        setSteps(activeSteps);
        return;
      }

      if (data.step === 'complete') {
        eventSource.close();
        setTimeout(onComplete, 500);
        return;
      }

      if (data.status === 'running') {
        setActiveStepId(data.step);
      } else if (data.status === 'done') {
        setCompletedSteps(prev => ({ ...prev, [data.step]: true }));
      } else if (data.status === 'error') {
        setError(data.error);
        eventSource.close();
      }
    };

    eventSource.onerror = (err) => {
      setError("Connection to server lost.");
      eventSource.close();
    };

    return () => eventSource.close();
  }, [jobId, onComplete]);

  // Calculate percentage based on completed steps
  const completedCount = Object.keys(completedSteps).length;
  const progress = steps.length > 0 ? Math.round((completedCount / steps.length) * 100) : 0;

  return (
    <div className="page-content">
      <style>{spinnerStyle}</style>
      <div className="generation-page">
        <div className="generation-header">
          {error ? (
            <>
              <h1 style={{ color: '#ef4444' }}>Generation Stopped</h1>
              <p>An error occurred during course creation.</p>
            </>
          ) : (
            <>
              <h1>Generating your course</h1>
              <p>Our AI is running the generation pipeline...</p>
            </>
          )}
        </div>

        <div className="progress-card">
          <div className="progress-meta">
            <span className="progress-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {error ? (
                <span style={{ color: '#ef4444', fontWeight: 600 }}>Error: {error}</span>
              ) : (
                <>
                  <Spinner />
                  <span>Working on: {steps.find(s => s.id === activeStepId)?.label || 'Starting...'}</span>
                </>
              )}
            </span>
            <span className="progress-pct">{progress}%</span>
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${progress}%`, background: error ? '#f87171' : 'var(--brand)' }} />
          </div>

          <div className="steps-list">
            {steps.map((step) => {
              const isDone = completedSteps[step.id];
              const isActive = activeStepId === step.id && !isDone && !error;
              const isPending = !isDone && !isActive;
              
              let statusClass = 'pending';
              if (isDone) statusClass = 'done';
              else if (isActive) statusClass = 'active';
              else if (error && activeStepId === step.id) statusClass = 'errored';

              return (
                <div key={step.id} className={`step-item ${statusClass}`}>
                  <div className={`step-icon-wrap ${statusClass}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {isDone ? (
                      <IconCheck size={18} />
                    ) : isActive ? (
                      <Spinner />
                    ) : error && activeStepId === step.id ? (
                      <span style={{ color: '#ef4444', fontWeight: 'bold', fontSize: 15 }}>✗</span>
                    ) : (
                      <div style={{ width: 8, height: 8, borderRadius: 4, background: 'currentColor' }} />
                    )}
                  </div>
                  <div className="step-body">
                    <div className={`step-name${isPending ? ' muted' : ''}`}>{step.label}</div>
                    <div className={`step-desc${isPending ? ' muted' : ''}`}>{step.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {error && onBack && (
            <div style={{ marginTop: 30, display: 'flex', justifyContent: 'center' }}>
              <button 
                onClick={onBack}
                style={{ 
                  background: '#334155', 
                  color: '#fff', 
                  border: 'none', 
                  padding: '10px 24px', 
                  borderRadius: 4, 
                  cursor: 'pointer', 
                  fontWeight: 600,
                  fontSize: 14,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}
              >
                <IconArrowLeft size={16} />
                Go Back to Editor
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
