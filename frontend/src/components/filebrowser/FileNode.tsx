// frontend/src/components/filebrowser/FileNode.tsx
import { useClientStore } from '@/stores/clientStore';
import type { FileNode as FileNodeType } from '@/types';
import { VscChevronRight, VscChevronDown, VscFile, VscFolder, VscFolderOpened } from 'react-icons/vsc';

interface Props {
  node: FileNodeType;
  depth: number;
}

export function FileNode({ node, depth }: Props) {
  const { expandedFolders, toggleFolder, selectFile, selectedFile, ingestionStatus } = useClientStore();
  const isExpanded = expandedFolders.has(node.path);
  const isSelected = selectedFile === node.path;
  const status = ingestionStatus[node.path];

  if (node.type === 'folder') {
    return (
      <div>
        <button
          type="button"
          onClick={() => toggleFolder(node.path)}
          className={`flex items-center w-full px-1 py-0.5 text-xs text-text-secondary hover:bg-bg-hover hover:text-text-primary transition-colors rounded`}
          style={{ paddingLeft: `${depth * 12 + 4}px` }}
        >
          {isExpanded ? <VscChevronDown size={16} className="shrink-0" /> : <VscChevronRight size={16} className="shrink-0" />}
          {isExpanded ? <VscFolderOpened size={16} className="shrink-0 ml-1 text-accent" /> : <VscFolder size={16} className="shrink-0 ml-1 text-accent" />}
          <span className="ml-1.5 truncate">{node.name}</span>
        </button>
        {isExpanded && node.children?.map((child) => (
          <FileNode key={child.path} node={child} depth={depth + 1} />
        ))}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => selectFile(node.path)}
      className={`flex items-center w-full px-1 py-0.5 text-xs transition-colors rounded ${
        isSelected ? 'bg-accent/10 text-accent' : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
      }`}
      style={{ paddingLeft: `${depth * 12 + 4}px` }}
    >
      <span className="w-4 shrink-0" />
      <VscFile size={16} className="shrink-0 ml-1" />
      <span className="ml-1.5 truncate">{node.name}</span>
      {status === 'indexing' && <span className="ml-auto w-2 h-2 rounded-full bg-accent-bright animate-pulse-dot shrink-0" />}
      {status === 'done' && <span className="ml-auto w-2 h-2 rounded-full bg-accent shrink-0" />}
      {status === 'error' && <span className="ml-auto w-2 h-2 rounded-full bg-red-500 shrink-0" />}
    </button>
  );
}
