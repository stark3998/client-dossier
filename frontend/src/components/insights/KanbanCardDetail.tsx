import { VscClose } from 'react-icons/vsc';
import type { Engagement } from '@/types';
import InlineEdit from '@/components/common/InlineEdit';

interface Props {
  engagement: Engagement;
  onClose: () => void;
  onUpdate: (field: string, value: string) => Promise<void>;
}

export default function KanbanCardDetail({ engagement, onClose, onUpdate }: Props) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-bg-secondary border border-border-default rounded-md w-full max-w-lg p-6 animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <InlineEdit value={engagement.name} onSave={(v) => onUpdate('name', v)} className="text-lg font-medium" />
          <button onClick={onClose} className="text-text-muted hover:text-text-secondary" aria-label="Close">
            <VscClose className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-text-muted uppercase tracking-wide">Description</label>
            <InlineEdit value={engagement.description} onSave={(v) => onUpdate('description', v)} type="textarea" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-text-muted uppercase tracking-wide">Phase</label>
              <InlineEdit
                value={engagement.phase}
                onSave={(v) => onUpdate('phase', v)}
                type="select"
                options={['discovery', 'design', 'execute', 'deliver', 'sustain']}
              />
            </div>
            <div>
              <label className="text-xs text-text-muted uppercase tracking-wide">Status</label>
              <InlineEdit
                value={engagement.status}
                onSave={(v) => onUpdate('status', v)}
                type="select"
                options={['active', 'on-hold', 'completed', 'cancelled']}
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-text-muted uppercase tracking-wide">Team</label>
            <div className="flex flex-wrap gap-1 mt-1">
              {engagement.team.map((member, i) => (
                <span key={i} className="px-2 py-0.5 bg-accent/10 text-accent text-xs rounded-full">
                  {member}
                </span>
              ))}
            </div>
          </div>

          {engagement.start_date && (
            <div className="flex gap-4 text-xs text-text-secondary">
              <span>Start: {engagement.start_date}</span>
              {engagement.end_date && <span>End: {engagement.end_date}</span>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
