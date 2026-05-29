// frontend/src/components/filebrowser/FileTree.tsx
import { useClientStore } from '@/stores/clientStore';
import { FileNode } from './FileNode';

export function FileTree() {
  const { fileTree } = useClientStore();

  if (!fileTree) {
    return <div className="text-text-muted text-xs p-3">Select a client to browse files</div>;
  }

  return (
    <div className="text-sm">
      {fileTree.children?.map((node) => (
        <FileNode key={node.path} node={node} depth={0} />
      ))}
      {(!fileTree.children || fileTree.children.length === 0) && (
        <div className="text-text-muted text-xs p-3">No files found</div>
      )}
    </div>
  );
}
