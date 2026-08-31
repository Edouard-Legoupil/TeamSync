import { useEffect, useRef } from 'react'
import type { RefObject } from 'react'

/**
 * Attach the returned ref to an element and the callback fires when a
 * pointer-down lands anywhere outside that element (e.g. to close a menu).
 */
export function useClickAway<T extends HTMLElement>(
  onClickAway: () => void
): RefObject<T> {
  const ref = useRef<T>(null)
  const handlerRef = useRef(onClickAway)
  handlerRef.current = onClickAway

  useEffect(() => {
    function handlePointer(event: MouseEvent | TouchEvent) {
      const element = ref.current
      const target = event.target
      if (
        element &&
        target instanceof Node &&
        !element.contains(target)
      ) {
        handlerRef.current()
      }
    }

    document.addEventListener('mousedown', handlePointer)
    document.addEventListener('touchstart', handlePointer)
    return () => {
      document.removeEventListener('mousedown', handlePointer)
      document.removeEventListener('touchstart', handlePointer)
    }
  }, [])

  return ref
}
