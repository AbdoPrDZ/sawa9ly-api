import { useState } from 'react'
import { createUser, deleteUser, listUsers, updateUser } from '../api/users'
import type { AdminUser, NewUser, UserEdits } from '../api/types'
import { Banner } from '../components/Banner'
import { PageHeader } from '../components/PageHeader'
import { Pager } from '../components/Pager'
import { RoleBadge } from '../components/RoleBadge'
import { SearchInput } from '../components/SearchInput'
import { MessageSpinner } from '../components/Spinner'
import { TablePanel } from '../components/TablePanel'
import { PAGE_SIZE, usePagedList } from '../hooks/usePagedList'
import { CreateUserModal } from '../features/users/CreateUserModal'
import { DeleteUserModal } from '../features/users/DeleteUserModal'
import { EditUserModal } from '../features/users/EditUserModal'
import { apiErrorMessage } from '../i18n/apiError'
import { useI18n } from '../i18n/useI18n'
import { useSession } from '../session/useSession'

/** Trim a long value for a cell without hiding that it was shortened. */
function brief(value: string | null, max = 30): string | null {
  if (!value) return null
  return value.length > max ? `${value.slice(0, max - 1)}…` : value
}

export function Users() {
  const { user: me, invalidate } = useSession()
  const { t } = useI18n()
const [notice, setNotice] = useState('')
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<AdminUser | null>(null)
  const [removing, setRemoving] = useState<AdminUser | null>(null)

  // Editing existing users is super-only. The controls are hidden rather than
  // disabled-and-explained, so an admin's page shows what they can actually do.
  const isSuper = me?.role === 'super'

  const list = usePagedList<AdminUser>(listUsers, {
    errorKey: 'error.users',
    // A rejected token is a session problem, not a page problem, so it is handed
    // back to the session rather than reported here.
    onUnauthorized: invalidate,
  })
  const users = list.items

  async function onCreate(input: NewUser) {
    try {
      await createUser(input)
      setCreating(false)
      setNotice(t('users.added'))
      list.reload()
    } catch (caught) {
      list.setError(apiErrorMessage(caught, t, 'error.users'))
    }
  }

  async function onSave(id: number, edits: UserEdits) {
    try {
      await updateUser(id, edits)
      setEditing(null)
      setNotice(t('users.updated'))
      list.reload()
    } catch (caught) {
      list.setError(apiErrorMessage(caught, t, 'error.users'))
    }
  }

  async function onDelete(target: AdminUser) {
    try {
      await deleteUser(target.id)
      setRemoving(null)
      setNotice(t('users.deleted', { name: target.username }))
      list.reload()
    } catch (caught) {
      list.setError(apiErrorMessage(caught, t, 'error.users'))
      setRemoving(null)
    }
  }

  return (
    <section>
      <PageHeader title={t('users.title')}>
        <button type="button" className="btn btn-primary" onClick={() => setCreating(true)}>
          {t('users.add')}
        </button>
      </PageHeader>

{list.error ? <Banner kind="error">{list.error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      {!isSuper ? <Banner kind="info">{t('users.adminBanner')}</Banner> : null}

      <div className="mb-4 max-w-sm">
        <SearchInput
          value={list.query.term}
          onChange={list.query.setTerm}
          placeholder={t('list.searchBy', { resource: t('resource.users') })}
          label={t('list.search')}
          busy={list.busy}
        />
      </div>

      {!users ? (
        <MessageSpinner messageKey="loading.users" />
      ) : (
        <TablePanel>
          <thead>
            <tr>
              <th>{t('users.col.username')}</th>
              <th>{t('users.col.role')}</th>
              <th>{t('users.col.sawa9ly')}</th>
              <th>{t('users.col.telegram')}</th>
              <th>{t('users.col.keys')}</th>
              <th>{t('users.col.orders')}</th>
              <th>{t('users.col.dashboard')}</th>
              {isSuper ? <th /> : null}
            </tr>
          </thead>
          <tbody>
            {users.map((row) => (
              <tr key={row.id}>
                <td className="font-medium">
                  {row.username}
                  {me?.id === row.id ? (
                    <span className="ms-1.5 text-xs text-faint">{t('generic.you')}</span>
                  ) : null}
                </td>
                <td>
                  <RoleBadge role={row.role} />
                </td>
                {/* Whether the user has set their own, not the value: it is
                    theirs, and an admin only needs to know it is done. */}
                <td>{row.has_sawa9ly_credentials ? t('users.set') : t('users.notSet')}</td>
                <td className="font-mono text-xs text-muted">
                  {brief(row.telegram_chat_id) ?? t('generic.unknown')}
                </td>
                <td>{row.active_api_keys}</td>
                <td>{row.orders}</td>
                <td>{row.can_log_in ? t('users.canSignIn') : t('users.noPassword')}</td>
                {isSuper ? (
                  <td>
                    <div className="flex justify-end gap-1.5">
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        disabled={!row.can_be_managed}
                        title={row.can_be_managed ? undefined : t('users.superManaged')}
                        onClick={() => setEditing(row)}
                      >
                        {t('generic.edit')}
                      </button>
                      <button
                        type="button"
                        className="btn btn-danger btn-sm"
                        disabled={!row.can_be_managed || me?.id === row.id}
                        title={deleteTitle(row, me?.id, t)}
                        onClick={() => setRemoving(row)}
                      >
                        {t('generic.delete')}
                      </button>
                    </div>
                  </td>
                ) : null}
              </tr>
            ))}
</tbody>
        </TablePanel>
      )}

      {users && users.length > 0 && (
        <Pager
          total={list.total}
          page={list.query.page}
          pageSize={PAGE_SIZE}
          hasMore={list.hasMore}
          onPage={list.query.setPage}
        />
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


/** Why the delete button is disabled, so the reason is visible on hover. */
function deleteTitle(row: AdminUser, meId: number | undefined, t: (key: 'users.superManaged' | 'users.cannotDeleteSelf') => string): string | undefined {
  if (!row.can_be_managed) return t('users.superManaged')
  if (row.id === meId) return t('users.cannotDeleteSelf')
  return undefined
}
