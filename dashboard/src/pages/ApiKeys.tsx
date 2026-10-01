import { useEffect, useMemo, useState } from 'react'
import { createKey, createMyKey, listKeys, listMyKeys, revokeKey, revokeMyKey } from '../api/keys'
import type { AdminApiKey, AdminUser } from '../api/types'
import { listUsers } from '../api/users'
import { Banner } from '../components/Banner'
import { KeyState } from '../components/KeyState'
import { PageHeader } from '../components/PageHeader'
import { Pager } from '../components/Pager'
import { SearchInput } from '../components/SearchInput'
import { MessageSpinner } from '../components/Spinner'
import { TablePanel } from '../components/TablePanel'
import { PAGE_SIZE, usePagedList } from '../hooks/usePagedList'
import { IssueKeyModal } from '../features/keys/IssueKeyModal'
import type { IssueKeyInput } from '../features/keys/IssueKeyModal'
import { RevealKeyModal } from '../features/keys/RevealKeyModal'
import { RevokeKeyModal } from '../features/keys/RevokeKeyModal'
import { apiErrorMessage } from '../i18n/apiError'
import { useI18n } from '../i18n/useI18n'
import { useSession } from '../session/useSession'

/** API keys, and who they belong to.
 *
 * Every signed-in user gets this page, because a key is the caller's own
 * credential: they mint it, they see it, they revoke it, and none of that needs
 * anybody else in the room. The three things that do need permission are held
 * back here rather than by hiding the page:
 *
 * - an admin sees every user's keys, a plain user only their own;
 * - only a `super` is offered the picker to issue a key for somebody else;
 * - the Issue button is disabled only for a `super` with no users to choose
 *   from, since a plain user always has somebody to issue for — themselves.
 *
 * The two issuing routes are chosen on `userId` being absent rather than on role
 * here as well, so the decision is made once, from what the form actually
 * collected.
 */
export function ApiKeys() {
  const { user, invalidate } = useSession()
  const { t } = useI18n()
const [users, setUsers] = useState<AdminUser[]>([])
  const [notice, setNotice] = useState('')
  const [issuing, setIssuing] = useState(false)
  const [revoking, setRevoking] = useState<AdminApiKey | null>(null)
  const [onlyLive, setOnlyLive] = useState(false)
  const [fresh, setFresh] = useState<string | null>(null)

  const seesEveryone = Boolean(user?.is_admin)
  const isSuper = user?.role === 'super'

  const list = usePagedList<AdminApiKey>(seesEveryone ? listKeys : listMyKeys, {
    errorKey: 'error.keys',
    onUnauthorized: invalidate,
    fetcherKey: seesEveryone ? 'all' : 'own',
  })
  const keys = list.items

  useEffect(() => {
    // The user list only populates the super's picker, so nobody else asks for
    // it, and a failure there is not worth a message of its own.
    if (!isSuper) return

    listUsers({ limit: 200 })
      .then((result) => setUsers(result.items))
      .catch(() => setUsers([]))
  }, [isSuper])

  const shown = useMemo(
    () => (keys ?? []).filter((key) => (onlyLive ? key.usable : true)),
    [keys, onlyLive],
  )

  async function onIssue(input: IssueKeyInput) {
    try {
      // No user in the form means the form had nobody to offer, so the key is the
      // reader's own — the self-service route, which takes no user at all.
      const created =
        input.userId === null
          ? await createMyKey(input.label, input.days)
          : await createKey(input.userId, input.label, input.days)

setIssuing(false)
      list.setError('')
      // The plaintext exists only in this response, so it is shown once and
      // then dropped; it cannot be fetched again.
      setFresh(created.key ?? null)
      list.reload()
    } catch (caught) {
      list.setError(apiErrorMessage(caught, t, 'error.keys'))
    }
  }

  async function onRevoke(target: AdminApiKey) {
    try {
      if (seesEveryone) await revokeKey(target.id)
      else await revokeMyKey(target.id)

      setNotice(t('keys.revoked', { prefix: target.prefix }))
      setRevoking(null)
      list.reload()
    } catch (caught) {
      list.setError(apiErrorMessage(caught, t, 'error.keys'))
      setRevoking(null)
    }
  }

  return (
    <section>
      <PageHeader title={t('keys.title')}>
        <label className="flex cursor-pointer items-center gap-2 rounded-control border border-line bg-raised px-2.5 py-[0.4375rem] text-xs text-muted transition-colors duration-150 hover:border-line-strong hover:text-ink">
          <input
            type="checkbox"
            checked={onlyLive}
            onChange={(event) => setOnlyLive(event.target.checked)}
          />
          {t('keys.filterUsable')}
        </label>
        <button
          type="button"
          className="btn btn-primary"
          disabled={isSuper && users.length === 0}
          title={isSuper && users.length === 0 ? t('keys.createFirst') : undefined}
          onClick={() => setIssuing(true)}
        >
          {t('generic.issue')}
        </button>
      </PageHeader>

      {/* The one thing a plain user cannot do, said plainly rather than left to be
          discovered as a 403 on the picker. */}
      {seesEveryone && !isSuper ? <Banner kind="info">{t('keys.adminBanner')}</Banner> : null}

{list.error ? <Banner kind="error">{list.error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      <div className="mb-4 max-w-sm">
        <SearchInput
          value={list.query.term}
          onChange={list.query.setTerm}
          placeholder={t('list.searchBy', { resource: t('resource.keys') })}
          label={t('list.search')}
          busy={list.busy}
        />
      </div>

      {!keys ? (
        <MessageSpinner messageKey="loading.keys" />
      ) : (
        <TablePanel>
          <thead>
            <tr>
              <th>{t('keys.col.prefix')}</th>
              <th>{t('keys.col.label')}</th>
              {seesEveryone ? <th>{t('keys.col.user')}</th> : null}
              <th>{t('keys.col.state')}</th>
              <th>{t('keys.col.lastUsed')}</th>
              <th>{t('keys.col.expires')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {shown.map((key) => (
              <tr key={key.id}>
                <td>
                  <code className="bg-transparent p-0 text-xs">{key.prefix}…</code>
                </td>
                <td className="font-medium">{key.label ?? t('generic.unknown')}</td>
                {seesEveryone ? <td>{key.username ?? `#${key.user_id}`}</td> : null}
                <td>
                  <KeyState revoked={key.revoked} usable={key.usable} />
                </td>
                <td className="text-muted">{key.last_used_at ?? t('generic.never')}</td>
                <td className="text-muted">{key.expires_at ?? t('generic.never')}</td>
                <td className="text-end">
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    disabled={key.revoked}
                    onClick={() => setRevoking(key)}
                  >
                    {t('generic.revoke')}
                  </button>
                </td>
              </tr>
            ))}
{shown.length === 0 ? (
              <tr>
                <td colSpan={seesEveryone ? 7 : 6} className="py-10 text-center text-muted">
                  {/* A page can be non-empty and still show nothing once the
                      usable filter is applied, so the three cases are named
                      separately rather than collapsed into one message. */}
                  {list.query.q
                    ? t('key.emptySearch')
                    : onlyLive
                      ? t('keys.noUsable')
                      : t('keys.noKeys')}
                </td>
              </tr>
            ) : null}
</tbody>
        </TablePanel>
      )}

      {keys && keys.length > 0 && (
        <Pager
          total={list.total}
          page={list.query.page}
          pageSize={PAGE_SIZE}
          hasMore={list.hasMore}
          onPage={list.query.setPage}
        />
      )}

      {issuing ? (
        <IssueKeyModal
          users={isSuper ? users : []}
          onCancel={() => setIssuing(false)}
          onSubmit={onIssue}
        />
      ) : null}

      {revoking ? (
        <RevokeKeyModal
          apiKey={revoking}
          onCancel={() => setRevoking(null)}
          onConfirm={() => onRevoke(revoking)}
        />
      ) : null}

      {fresh ? <RevealKeyModal secret={fresh} onClose={() => setFresh(null)} /> : null}
    </section>
  )
}

