import { useEffect, useState } from 'react'

/** How long the search box stays quiet before a request goes out. */
export const SEARCH_DEBOUNCE_MS = 800

/**
 * A search box that waits for typing to stop before anything happens.
 *
 * Returns the raw value the box shows and the debounced value a fetch should use.
 * Keeping both is the whole trick: the box has to update on every keystroke or it
 * feels broken, but fetching on every keystroke would put a request per character
 * on the wire.
 *
 * An empty box settles to `''` rather than staying `undefined`, so callers can
 * treat "no search" as falsy without a second check.
 */
export function useDebouncedSearch(raw: string, delay = SEARCH_DEBOUNCE_MS): string {
  const [settled, setSettled] = useState(raw)

  useEffect(() => {
    // No timer when the term is already what the caller asked for: on first
    // render that would delay the first fetch by the full debounce for nothing.
    if (raw === settled) return

    const timer = window.setTimeout(() => setSettled(raw), delay)

    // Clearing on the way out is what makes it a debounce rather than a delay:
    // every further keystroke discards the pending timer and starts over.
    return () => window.clearTimeout(timer)
  }, [raw, settled, delay])

  return settled
}

/** The search term and page number a list screen is on. */
export interface ListQueryState {
  /** What is in the box right now, for showing back to the user. */
  term: string
  /** What to send to the server: settled, and safe to put in a query string. */
  q: string
  /** Zero-based index of the page on screen. */
  page: number
  /** Call when the box changed, whatever it changed to. */
  setTerm: (value: string) => void
  /** Call to go to a page. Clamped to the last page the server has. */
  setPage: (value: number) => void
}

/**
 * Search and paging for a list screen, tied together.
 *
 * The one behaviour worth spelling out: changing the search resets to page 0.
 * Without that, searching while on page 5 asks for rows 200-249 of a result set
 * that may only hold three, and the user gets an empty table and no idea why.
 *
 * The page size is not decided here: `usePagedList` owns it, and sends it on
 * every request including the first, so the count the server returns and the
 * rows it returns always agree.
 */
export function useListQuery(): ListQueryState {
  const [term, setTerm] = useState('')
  const [page, setPage] = useState(0)
  const q = useDebouncedSearch(term)

  // Keyed on the settled term rather than the raw one, so a page reset happens
  // once per search and not once per character typed into it.
  useEffect(() => {
    setPage(0)
  }, [q])

  return {
    term,
    q,
    page,
    setTerm,
    setPage: (value: number) => setPage(Math.max(0, value)),
  }
}