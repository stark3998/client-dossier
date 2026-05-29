import { VscSearch } from 'react-icons/vsc';
import { useClientStore } from '@/stores/clientStore';

export default function SearchBar() {
  const { setCommandPaletteOpen } = useClientStore();

  return (
    <button
      onClick={() => setCommandPaletteOpen(true)}
      className="flex items-center gap-2 px-3 py-1.5 bg-bg-primary border border-border-default rounded-md text-text-muted text-sm hover:border-text-muted transition-colors"
      aria-label="Search (Ctrl+K)"
    >
      <VscSearch className="w-3.5 h-3.5" />
      <span className="hidden sm:inline font-mono text-xs">Search...</span>
      <kbd className="hidden sm:inline text-[10px] bg-bg-secondary px-1.5 py-0.5 rounded border border-border-default">
        Ctrl+K
      </kbd>
    </button>
  );
}
