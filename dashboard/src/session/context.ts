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
}

export const SessionContext = createContext<Session | null>(null)