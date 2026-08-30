import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

interface ProgressContextValue {
  start: () => void
  stop: () => void
  active: boolean
}

const ProgressContext = createContext<ProgressContextValue | undefined>(undefined)

/**
 * A subtle, non-blocking top progress bar. Call `start()`/`stop()` around any
 * background work (e.g. transcript processing) instead of blocking the UI.
 */
export function ProgressProvider({ children }: { children: ReactNode }) {
  const [count, setCount] = useState(0)

  const start = useCallback(() => setCount((c) => c + 1), [])
  const stop = useCallback(() => setCount((c) => Math.max(0, c - 1)), [])
  const active = count > 0

  const value = useMemo(() => ({ start, stop, active }), [start, stop, active])

  return (
    <ProgressContext.Provider value={value}>
      {active && (
        <div className="fixed inset-x-0 top-0 z-[60] h-0.5 overflow-hidden bg-primary-100">
          <div className="animate-progress h-full w-1/4 bg-primary-600" />
        </div>
      )}
      {children}
    </ProgressContext.Provider>
  )
}

export function useProgress(): ProgressContextValue {
  const ctx = useContext(ProgressContext)
  if (!ctx) throw new Error('useProgress must be used within a ProgressProvider')
  return ctx
}
