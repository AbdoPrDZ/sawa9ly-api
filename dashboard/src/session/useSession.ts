import { useContext } from 'react'
import { SessionContext, type Session } from './context'

export function useSession(): Session {
  const session = useContext(SessionContext)

  if (!session) throw new Error('useSession must be used inside a SessionProvider')

  return session
}