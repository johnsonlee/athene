import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="rounded-lg border border-red-300 bg-red-50 p-6 text-center dark:border-red-700 dark:bg-red-900/30">
            <h2 className="text-lg font-semibold text-red-800 dark:text-red-400">Something went wrong</h2>
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">{this.state.error?.message}</p>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
