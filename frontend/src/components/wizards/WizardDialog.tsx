import { useState } from 'react';
import { VscClose } from 'react-icons/vsc';

export interface WizardStep {
  title: string;
  content: React.ReactNode;
  validate?: () => boolean;
}

interface Props {
  title: string;
  steps: WizardStep[];
  onComplete: () => void;
  onCancel: () => void;
}

export default function WizardDialog({ title, steps, onComplete, onCancel }: Props) {
  const [current, setCurrent] = useState(0);

  const canNext = !steps[current].validate || steps[current].validate();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onCancel}>
      <div
        className="bg-bg-secondary border border-border-default rounded-md w-full max-w-2xl max-h-[80vh] flex flex-col animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-default">
          <h2 className="text-text-primary font-medium">{title}</h2>
          <button onClick={onCancel} className="text-text-muted hover:text-text-secondary" aria-label="Close">
            <VscClose className="w-5 h-5" />
          </button>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2 px-6 py-3 border-b border-border-default">
          {steps.map((step, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono ${
                i < current ? 'bg-accent text-bg-primary' :
                i === current ? 'border-2 border-accent text-accent' :
                'border border-border-default text-text-muted'
              }`}>
                {i < current ? '✓' : i + 1}
              </div>
              <span className={`text-xs ${i === current ? 'text-text-primary' : 'text-text-muted'}`}>
                {step.title}
              </span>
              {i < steps.length - 1 && <div className="w-8 h-px bg-border-default" />}
            </div>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {steps[current].content}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border-default">
          <button
            onClick={() => current > 0 ? setCurrent(current - 1) : onCancel()}
            className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary"
          >
            {current === 0 ? 'Cancel' : 'Back'}
          </button>
          <button
            onClick={() => {
              if (current < steps.length - 1) setCurrent(current + 1);
              else onComplete();
            }}
            disabled={!canNext}
            className="px-4 py-2 text-sm bg-accent text-bg-primary rounded-md hover:bg-accent-bright disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {current === steps.length - 1 ? 'Create' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
}
