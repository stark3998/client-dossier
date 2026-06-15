import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-bg-primary flex items-center justify-center p-8">
          <div className="max-w-lg w-full bg-bg-panel border border-red-500/40 rounded-md p-6">
            <h1 className="text-base font-semibold text-red-400 mb-2">Something went wrong</h1>
            <p className="text-sm text-text-secondary mb-4">
              An unexpected error prevented the app from rendering.
            </p>
            <pre className="text-xs text-text-muted bg-bg-secondary rounded p-3 overflow-auto max-h-48 whitespace-pre-wrap mb-4">
              {this.state.error.message}
            </pre>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-4 py-2 text-sm font-medium bg-accent text-bg-primary rounded hover:bg-accent-bright transition-colors"
            >
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
