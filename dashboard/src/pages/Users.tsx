import { useCallback, useEffect, useState } from 'react'
import { isUnauthorized } from '../api/client'
import { createUser, deleteUser, listUsers, updateUser } from '../api/users'
import type { AdminUser, NewUser, UserEdits } from '../api/types'
import { Banner } from '../components/Banner'
import { RoleBadge } from '../components/RoleBadge'
import { Spinner } from '../components/Spinner'
import { CreateUserModal } from '../features/users/CreateUserModal'
import { DeleteUserModal } from '../features/users/DeleteUserModal'
import { EditUserModal } from '../features/users/EditUserModal'
import { useSession } from '../session/useSession'

/** Trim a long value for a cell without hiding that it was shortened. */
function brief(value: string | null, max = 30): string {
  if (!value) return '—'
  return value.length > max ? `${value.slice(0, max - 1)}…` : value
}

export function Users() {
  const { user: me, invalidate } = useSession()
  const [users, setUsers] = useState<AdminUser[] | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<AdminUser | null>(null)
  const [removing, setRemoving] = useState<AdminUser | null>(null)

  // Editing existing users is super-only. The controls are hidden rather than
  // disabled-and-explained, so an admin's page shows what they can actually do.
  const isSuper = me?.role === 'super'

  const load = useCallback(async () => {
    try {
      setUsers(await listUsers())
    } catch (caught) {
      // A rejected token is a session problem, not a page problem, so it is
      // handed back to the session rather than reported here.
      if (isUnauthorized(caught)) return invalidate()
      setError(message(caught, 'Could not load users.'))
    }
  }, [invalidate])

  useEffect(() => {
    load()
  }, [load])

  async function onCreate(input: NewUser) {
    try {
      await createUser(input)
      setCreating(false)
      setNotice('User added.')
      await load()
    } catch (caught) {
      setError(message(caught, 'Could not create the user.'))
    }
  }

  async function onSave(id: number, edits: UserEdits) {
    try {
      await updateUser(id, edits)
      setEditing(null)
      setNotice('User updated.')
      await load()
    } catch (caught) {
      setError(message(caught, 'Could not save the user.'))
    }
  }

  async function onDelete(target: AdminUser) {
    try {
      await deleteUser(target.id)
      setRemoving(null)
      setNotice(`Deleted ${target.username}.`)
      await load()
    } catch (caught) {
      setError(message(caught, 'Could not delete the user.'))
      setRemoving(null)
    }
  }

  return (
    <section>
      <div className="section-head">
        <h2>Users</h2>
        <button type="button" className="primary" onClick={() => setCreating(true)}>
          Add user
        </button>
      </div>

      {error ? <Banner kind="error">{error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      {!isSuper ? (
        <Banner kind="info">
          As an administrator you can add users. Editing or deleting an existing account needs
          the super role.
        </Banner>
      ) : null}

      {!users ? (
        <Spinner label="Loading users" />
      ) : (
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Role</th>
              <th>Sawa9ly</th>
              <th>Telegram</th>
              <th>Keys</th>
              <th>Orders</th>
              <th>Dashboard</th>
              {isSuper ? <th /> : null}
            </tr>
          </thead>
          <tbody>
            {users.map((row) => (
              <tr key={row.id}>
                <td>
                  {row.username}
                  {me?.id === row.id ? <span className="muted"> (you)</span> : null}
                </td>
                <td>
                  <RoleBadge role={row.role} />
                </td>
                {/* Whether the user has set their own, not the value: it is
                    theirs, and an admin only needs to know it is done. */}
                <td>{row.has_sawa9ly_credentials ? 'set' : 'not set'}</td>
                <td>{brief(row.telegram_chat_id)}</td>
                <td>{row.active_api_keys}</td>
                <td>{row.orders}</td>
                <td>{row.can_log_in ? 'can sign in' : 'no password'}</td>
                {isSuper ? (
                  <td className="row-actions">
                    <button
                      type="button"
                      className="ghost"
                      disabled={!row.can_be_managed}
                      title={
                        row.can_be_managed ? undefined : 'A super account is managed from the CLI'
                      }
                      onClick={() => setEditing(row)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="danger"
                      disabled={!row.can_be_managed || me?.id === row.id}
                      title={deleteTitle(row, me?.id)}
                      onClick={() => setRemoving(row)}
                    >
                      Delete
                    </button>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {creating ? (
        <CreateUserModal onCancel={() => setCreating(false)} onSubmit={onCreate} />
      ) : null}

      {editing ? (
        <EditUserModal
          user={editing}
          isSelf={me?.id === editing.id}
          onCancel={() => setEditing(null)}
          onSubmit={(edits) => onSave(editing.id, edits)}
        />
      ) : null}

      {removing ? (
        <DeleteUserModal
          user={removing}
          onCancel={() => setRemoving(null)}
          onConfirm={() => onDelete(removing)}
        />
      ) : null}
    </section>
  )
}

function message(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback
}

/** Why the delete button is disabled, so the reason is visible on hover. */
function deleteTitle(row: AdminUser, meId?: number): string | undefined {
  if (!row.can_be_managed) return 'A super account is managed from the CLI'
  if (row.id === meId) return 'You cannot delete your own account'
  return undefined
}
