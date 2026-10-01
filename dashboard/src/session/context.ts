import { createContext } from 'react'
import type { SessionUser } from '../api/types'

export interface Session {
  user: SessionUser | null
  /** True until a stored token has been checked against the server. */
  loading: boolean
  signIn(username: string, password: string): Promise<void>
  signOut(): void
  /** Called when the server rejects the token, so one place clears it. */
  invalidate(): void
  /** Re-read the signed-in user, keeping the token.
   *
   * Separate from `invalidate`, which signs out. Needed because the language
   * lives on the user: changing it is a `PATCH /me/profile`, and the shell reads
   * the language from the session, so the session has to be told — otherwise the
   * interface would keep rendering in the old one until a reload.
   */
  refresh(): Promise<void>
}

export const SessionContext = createContext<Session | null>(null)