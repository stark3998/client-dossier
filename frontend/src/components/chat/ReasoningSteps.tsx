// frontend/src/components/chat/ReasoningSteps.tsx
import type { AgentReasoningStep } from '@/types';

interface Props {
  steps: AgentReasoningStep[];
}

function StepContent({ step }: { step: AgentReasoningStep }) {
  switch (step.type) {
    case 'thought':
      return (
        <p className="text-text-muted font-mono text-xs italic">
          <span className="text-text-secondary">Thinking:</span> {step.content}
        </p>
      );
    case 'plan':
      return (
        <div>
          <span className="text-xs font-medium text-text-secondary">Plan:</span>
          <ol className="list-decimal list-inside mt-1 space-y-0.5">
            {(step.plan_steps ?? []).map((s, i) => (
              <li key={i} className="text-xs text-text-secondary">{s}</li>
            ))}
          </ol>
        </div>
      );
    case 'tool_call':
      return (
        <div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium text-accent-blue">
              Tool: {step.tool_name}
            </span>
            {step.tool_source === 'mcp' && (
              <span className="text-[9px] px-1.5 py-0.5 bg-accent-blue/10 text-accent-blue rounded font-medium">MCP</span>
            )}
          </div>
          {step.tool_args && (
            <pre className="text-[10px] text-text-muted mt-0.5 overflow-x-auto">
              {JSON.stringify(step.tool_args, null, 2)}
            </pre>
          )}
        </div>
      );
    case 'tool_result':
      return (
        <div>
          <span className="text-xs font-medium text-text-secondary">Result:</span>
          <div className="text-xs text-text-secondary mt-0.5 max-h-24 overflow-auto font-mono">
            {step.content}
          </div>
        </div>
      );
    case 'plan_step':
      return (
        <p className="text-xs text-text-secondary">
          <span className="text-status-green mr-1">&#10003;</span>
          {step.content}
          {step.step_number != null && step.step_total != null && (
            <span className="text-text-muted ml-1">
              ({step.step_number}/{step.step_total})
            </span>
          )}
        </p>
      );
  }
}

export function ReasoningSteps({ steps }: Props) {
  if (steps.length === 0) return null;

  return (
    <div className="max-h-[200px] overflow-auto">
      <div className="space-y-1">
        {steps.map((step, i) => (
          <details key={i} className="group">
            <summary className="text-[10px] text-text-muted cursor-pointer select-none hover:text-text-secondary">
              {step.type === 'thought' && 'Thinking...'}
              {step.type === 'plan' && 'Plan'}
              {step.type === 'tool_call' && `Tool: ${step.tool_name ?? 'unknown'}`}
              {step.type === 'tool_result' && 'Result'}
              {step.type === 'plan_step' && `Step ${step.step_number ?? ''}`}
            </summary>
            <div className="pl-3 py-0.5">
              <StepContent step={step} />
            </div>
          </details>
        ))}
      </div>
      <div className="border-t border-border-default mt-2 pt-2" />
    </div>
  );
}
