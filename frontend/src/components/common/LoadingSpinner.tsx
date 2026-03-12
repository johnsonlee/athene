export function LoadingSpinner({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="relative">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-300 border-t-cyan-500 dark:border-gray-700 dark:border-t-cyan-400" />
        <div className="absolute inset-[-4px] animate-spin rounded-full border-2 border-transparent border-t-cyan-400/30 dark:border-t-cyan-300/20" style={{ animationDuration: '3s', animationDirection: 'reverse' }} />
      </div>
      <p className="mt-4 font-mono text-sm tracking-wide text-gray-500 dark:text-gray-400">{message}</p>
    </div>
  );
}
