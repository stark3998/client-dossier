import { useState } from 'react';
import WizardDialog from './WizardDialog';

const CATEGORIES = ['technical', 'commercial', 'operational', 'timeline'] as const;

interface Props {
  clientName: string;
  engagementId: string;
  onComplete: () => void;
  onCancel: () => void;
}

export default function RiskAssessmentWizard({ clientName, engagementId, onComplete, onCancel }: Props) {
  const [category, setCategory] = useState<string>('operational');
  const [description, setDescription] = useState('');
  const [probability, setProbability] = useState(3);
  const [impact, setImpact] = useState(3);
  const [mitigation, setMitigation] = useState('');

  const base = import.meta.env.VITE_BACKEND_URL || '';
  const severity = probability * impact;

  const severityColor = severity >= 15 ? 'text-status-red' : severity >= 8 ? 'text-status-amber' : 'text-accent';

  const handleCreate = async () => {
    await fetch(`${base}/api/clients/${encodeURIComponent(clientName)}/engagements/${engagementId}/risks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: crypto.randomUUID(),
        description, probability, impact, category, mitigation,
        engagement_id: engagementId, status: 'open', owner: '',
      }),
    });
    onComplete();
  };

  const inputClass = "w-full bg-bg-primary border border-border-default rounded-md px-3 py-2 text-sm text-text-primary focus:border-accent outline-none";

  const steps = [
    {
      title: 'Category',
      content: (
        <div className="space-y-3">
          <label className="block text-sm text-text-secondary">Risk Category</label>
          <div className="grid grid-cols-2 gap-2">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => setCategory(c)}
                className={`px-4 py-3 rounded-md text-sm capitalize ${
                  category === c ? 'bg-accent text-bg-primary' : 'bg-bg-primary border border-border-default text-text-secondary hover:border-accent'
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
      ),
    },
    {
      title: 'Description',
      validate: () => description.trim().length > 0,
      content: (
        <div className="space-y-4">
          <label className="block text-sm text-text-secondary">Risk Description</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} className={`${inputClass} min-h-[100px]`} placeholder="Describe the risk..." />
        </div>
      ),
    },
    {
      title: 'Assessment',
      content: (
        <div className="space-y-6">
          <div>
            <label className="block text-sm text-text-secondary mb-2">Probability (1-5): {probability}</label>
            <input type="range" min={1} max={5} value={probability} onChange={(e) => setProbability(Number(e.target.value))} className="w-full accent-accent" />
          </div>
          <div>
            <label className="block text-sm text-text-secondary mb-2">Impact (1-5): {impact}</label>
            <input type="range" min={1} max={5} value={impact} onChange={(e) => setImpact(Number(e.target.value))} className="w-full accent-accent" />
          </div>
          <div className="text-center">
            <span className="text-text-muted text-sm">Severity Score: </span>
            <span className={`font-mono text-2xl font-bold ${severityColor}`}>{severity}</span>
          </div>
        </div>
      ),
    },
    {
      title: 'Mitigation',
      content: (
        <div className="space-y-4">
          <label className="block text-sm text-text-secondary">Mitigation Strategy</label>
          <textarea value={mitigation} onChange={(e) => setMitigation(e.target.value)} className={`${inputClass} min-h-[100px]`} placeholder="How will this risk be mitigated?" />
        </div>
      ),
    },
  ];

  return <WizardDialog title="Risk Assessment" steps={steps} onComplete={handleCreate} onCancel={onCancel} />;
}
