import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { token as tokenStore } from '../api/client'
import { login, me } from '../api/session'
import type { SessionUser } from '../api/types'
import { SessionContext, type Session } from './context'
import { isUnauthorized } from '../api/client'

/** Holds the signed-in user and keeps the token in step with the server. */
export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [loading, setLoading] = useState(true)

  const signOut = useCallback(() => {
    tokenStore.clear()
    setUser(null)
  }, [])

  // A stored token is not proof of anything: it may have expired, or the user
  // may have been demoted or deleted since it was issued. The server is asked
  // before the app shows anything at all.
  useEffect(() => {
    let cancelled = false

    async function restore() {
      if (!tokenStore.get()) {
        setLoading(false)
        return
      }

      try {
        const current = await me()
        if (!cancelled) setUser(current)
      } catch (error) {
        if (isUnauthorized(error) && !cancelled) tokenStore.clear()
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    restore()

    return () => {
      cancelled = true
    }
  }, [])

  const signIn = useCallback(async (username: string, password: string) => {
    const session = await login(username, password)
    tokenStore.set(session.token)
    setUser(session.user)
  }, [])

  // Re-read the user without touching the token. A rejected token here means the
  // session really is over, so it signs out rather than leaving a shell that
  // cannot load anything.
  const refresh = useCallback(async () => {
    try {
      setUser(await me())
    } catch (error) {
      if (isUnauthorized(error)) tokenStore.clear()
      setUser(null)
    }
  }, [])

  const value = useMemo<Session>(
    () => ({ user, loading, signIn, signOut, invalidate: signOut, refresh }),
    [user, loading, signIn, signOut, refresh],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}
