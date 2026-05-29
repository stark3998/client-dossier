import { useState } from 'react';
import WizardDialog from './WizardDialog';

const PHASES = ['discovery', 'design', 'execute', 'deliver', 'sustain'] as const;

interface Props {
  clientName: string;
  onComplete: () => void;
  onCancel: () => void;
}

export default function NewEngagementWizard({ clientName, onComplete, onCancel }: Props) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [phase, setPhase] = useState<string>('discovery');
  const [team, setTeam] = useState('');
  const [budget, setBudget] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const base = import.meta.env.VITE_BACKEND_URL || '';

  const handleCreate = async () => {
    await fetch(`${base}/api/clients/${encodeURIComponent(clientName)}/engagements`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: crypto.randomUUID(),
        name, description, phase, status: 'active',
        client_name: clientName,
        team: team.split(',').map((t) => t.trim()).filter(Boolean),
        budget: budget ? parseFloat(budget) : undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
    });
    onComplete();
  };

  const inputClass = "w-full bg-bg-primary border border-border-default rounded-md px-3 py-2 text-sm text-text-primary focus:border-accent outline-none";

  const steps = [
    {
      title: 'Name',
      validate: () => name.trim().length > 0,
      content: (
        <div className="space-y-4">
          <label className="block text-sm text-text-secondary">Engagement Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} className={inputClass} placeholder="e.g. Cloud Migration Phase 2" />
          <label className="block text-sm text-text-secondary">Description</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} className={`${inputClass} min-h-[80px]`} placeholder="Brief description..." />
        </div>
      ),
    },
    {
      title: 'Phase',
      content: (
        <div className="space-y-3">
          <label className="block text-sm text-text-secondary">Starting Phase</label>
          <div className="flex gap-2 flex-wrap">
            {PHASES.map((p) => (
              <button
                key={p}
                onClick={() => setPhase(p)}
                className={`px-4 py-2 rounded-md text-sm capitalize ${
                  phase === p ? 'bg-accent text-bg-primary' : 'bg-bg-primary border border-border-default text-text-secondary hover:border-accent'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      ),
    },
    {
      title: 'Team',
      content: (
        <div className="space-y-4">
          <label className="block text-sm text-text-secondary">Team Members (comma-separated)</label>
          <input value={team} onChange={(e) => setTeam(e.target.value)} className={inputClass} placeholder="Alice, Bob, Charlie" />
        </div>
      ),
    },
    {
      title: 'Details',
      content: (
        <div className="space-y-4">
          <label className="block text-sm text-text-secondary">Budget</label>
          <input type="number" value={budget} onChange={(e) => setBudget(e.target.value)} className={inputClass} placeholder="Optional" />
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-text-secondary mb-1">Start Date</label>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className="block text-sm text-text-secondary mb-1">End Date</label>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={inputClass} />
            </div>
          </div>
        </div>
      ),
    },
  ];

  return <WizardDialog title="New Engagement" steps={steps} onComplete={handleCreate} onCancel={onCancel} />;
}
