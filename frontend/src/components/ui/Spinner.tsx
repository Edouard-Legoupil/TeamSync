export function Spinner({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary-600 border-t-transparent ${className}`}
      aria-label="Loading"
    />
  )
}
