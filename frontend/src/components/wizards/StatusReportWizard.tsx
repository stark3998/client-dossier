import { useState, useEffect } from 'react';
import WizardDialog from './WizardDialog';
import type { Engagement } from '@/types';

interface Props {
  clientName: string;
  onComplete: (reportText: string) => void;
  onCancel: () => void;
}

export default function StatusReportWizard({ clientName, onComplete, onCancel }: Props) {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [reportData, setReportData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const base = import.meta.env.VITE_BACKEND_URL || '';

  useEffect(() => {
    fetch(`${base}/api/clients/${encodeURIComponent(clientName)}/engagements`)
      .then((r) => r.json())
      .then((d) => setEngagements(d.engagements || []))
      .catch(() => {});
  }, [clientName, base]);

  const fetchReport = async () => {
    if (!selectedId) return;
    setLoading(true);
    try {
      const res = await fetch(`${base}/api/tools/invoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plugin: 'Reporting',
          function: 'draft_status_report',
          arguments: { client_name: clientName, engagement_id: selectedId },
        }),
      });
      const data = await res.json();
      setReportData(typeof data.result === 'string' ? JSON.parse(data.result) : data);
    } catch {
      setReportData({ error: 'Failed to generate report' });
    }
    setLoading(false);
  };

  const steps = [
    {
      title: 'Engagement',
      validate: () => !!selectedId,
      content: (
        <div className="space-y-3">
          <label className="block text-sm text-text-secondary">Select Engagement</label>
          <div className="space-y-2">
            {engagements.map((e) => (
              <button
                key={e.id}
                onClick={() => setSelectedId(e.id)}
                className={`w-full text-left px-4 py-3 rounded-md ${
                  selectedId === e.id ? 'bg-accent/10 border border-accent' : 'bg-bg-primary border border-border-default hover:border-text-muted'
                }`}
              >
                <div className="text-sm text-text-primary">{e.name}</div>
                <div className="text-xs text-text-muted capitalize">{e.phase} · {e.status}</div>
              </button>
            ))}
            {engagements.length === 0 && (
              <p className="text-sm text-text-muted">No engagements found</p>
            )}
          </div>
        </div>
      ),
    },
    {
      title: 'Generate',
      content: (
        <div className="space-y-4">
          {!reportData && !loading && (
            <button onClick={fetchReport} className="px-4 py-2 bg-accent text-bg-primary rounded-md text-sm hover:bg-accent-bright">
              Generate Report
            </button>
          )}
          {loading && <p className="text-sm text-text-muted">Generating...</p>}
          {reportData && (
            <pre className="bg-bg-primary border border-border-default rounded-md p-3 text-xs text-text-secondary overflow-auto max-h-[300px] font-mono">
              {JSON.stringify(reportData, null, 2)}
            </pre>
          )}
        </div>
      ),
    },
    {
      title: 'Review',
      content: (
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">
            The status report data has been generated. You can send it to the agent for formatting.
          </p>
          <button
            onClick={() => {
              const text = `/draft status report for engagement ${selectedId}`;
              onComplete(text);
            }}
            className="px-4 py-2 bg-accent text-bg-primary rounded-md text-sm hover:bg-accent-bright"
          >
            Send to Agent
          </button>
        </div>
      ),
    },
  ];

  return <WizardDialog title="Status Report" steps={steps} onComplete={() => onComplete('')} onCancel={onCancel} />;
}
