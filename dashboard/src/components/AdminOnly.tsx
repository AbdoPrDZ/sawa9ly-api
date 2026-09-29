import type { ReactNode } from 'react'
import { useSession } from '../session/useSession'

/** Renders its children only for an administrator.
 *
 * Some of what this app can do belongs to the operator rather than to the user
 * sitting in front of it. A `python main.py … --user <name>` command is the
 * clearest example: it is how the operator seeds or fixes data on somebody else's
 * behalf, and there is nothing a non-admin can do with it.
 *
 * Hiding those by role rather than deleting them keeps the instruction next to
 * the thing it is about for the people who can act on it, and takes away the
 * dead end for the people who cannot. The server is the authority on roles;
 * this only decides what to draw.
 */
export function AdminOnly({ children }: { children: ReactNode }) {
  const { user } = useSession()

  if (!user?.is_admin) return null

  return <>{children}</>
}
