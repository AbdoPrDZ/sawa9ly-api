import { useCallback, useEffect, useState } from 'react'
import { getBinding, issueLink, sendTest, unbind } from '../../api/telegram'
import type { TelegramBinding, TelegramLink } from '../../api/types'
import { Banner } from '../../components/Banner'
import { MessageSpinner } from '../../components/Spinner'
import { useI18n } from '../../i18n/useI18n'

/** Linking this user's account to a Telegram chat.
 *
 * The link is shown once and then forgotten, because the code in it is stored
 * only as a hash — the same contract an API key has. Losing it is not a problem:
 * "Get a new link" makes a new one, and issuing one does not unbind the chat the
 * user already had.
 *
 * The card spans the profile grid, because the explanation of how to use the link
 * is longer than a column is wide.
 */
export function TelegramCard() {
  const { t } = useI18n()
  const [binding, setBinding] = useState<TelegramBinding | null>(null)
  const [link, setLink] = useState<TelegramLink | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [testing, setTesting] = useState(false)

  const load = useCallback(async () => {
    try {
      setBinding(await getBinding())
    } catch (caught) {
      setError(message(caught, t('error.telegram')))
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  async function getLink() {
    setError('')
    setNotice('')
    setBusy(true)
    try {
      setLink(await issueLink())
      await load()
    } catch (caught) {
      setError(message(caught, t('telegram.linkFailed')))
    } finally {
      setBusy(false)
    }
  }

  async function onUnbind() {
    setError('')
    setNotice('')
    setBusy(true)
    try {
      await unbind()
      setLink(null)
      await load()
    } catch (caught) {
      setError(message(caught, t('telegram.unbound')))
    } finally {
      setBusy(false)
    }
  }

  async function onTest() {
    setError('')
    setNotice('')
    setTesting(true)
    try {
      await sendTest()
      setNotice(t('telegram.testSent'))
    } catch (caught) {
      setError(message(caught, t('telegram.testFailed')))
    } finally {
      setTesting(false)
    }
  }

  if (!binding) return <MessageSpinner messageKey="loading.telegram" />

  return (
    <div className="card xl:col-span-2">
      <h3 className="mb-2">{t('telegram.title')}</h3>

      {error ? <Banner kind="error">{error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      {binding.bound ? (
        <>
          <p className="mb-3 max-w-prose text-sm text-muted">
            {t('telegram.bound', {
              chat:
                binding.chat_title ?? binding.chat_username ?? String(binding.chat_id),
              type: binding.chat_type ?? '',
            })}
          </p>
          {/* Real notifications are not wired up yet, so this is the only way
              to find out that a linked chat actually delivers. */}
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn" disabled={testing} onClick={onTest}>
              {testing ? t('telegram.testBusy') : t('telegram.test')}
            </button>
            <button type="button" className="btn" disabled={busy} onClick={onUnbind}>
              {t('telegram.unbind')}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="mb-3 max-w-prose text-sm text-muted">{t('telegram.unboundIntro')}</p>
          {binding.code_pending ? (
            <p className="mb-3 text-sm">
              {t('telegram.pending')}{' '}
              <span className="badge">
                {t('telegram.expires', { time: formatTime(binding.code_expires_at) })}
              </span>
            </p>
          ) : null}
          <button type="button" className="btn btn-primary" disabled={busy} onClick={getLink}>
            {busy ? t('telegram.working') : binding.code_pending ? t('telegram.getNewLink') : t('telegram.getLink')}
          </button>
        </>
      )}

      {link ? <LinkPanel link={link} onDismiss={() => setLink(null)} /> : null}
    </div>
  )
}

/** The one time the link is visible.
 *
 *  The page this opens has **two** buttons, and the obvious one is the one that
 * fails. "Start Bot" hands off to Telegram's app through the `tg://` scheme,
 * which a browser reports as *"scheme does not have a registered handler"* on a
 * computer with no Telegram app installed — the button then does nothing at all,
 * silently. "Open in Web" carries the same code in a `tgaddr` fragment and works
 * with no app, so the instruction names it rather than saying "open this link".
 *
 *  The code is offered alongside for the same reason: it works in every client,
 * installed or not.
 *
 *  Both button names are left in English, in every language. They are labels
 *  printed on a page this project does not control, so translating them would
 *  point at a button that is not there.
 */
function LinkPanel({ link, onDismiss }: { link: TelegramLink; onDismiss(): void }) {
  const { t } = useI18n()

  return (
    <div className="mt-5 border-t border-line pt-4">
      <Banner kind="info">
        {t('telegram.linkIntro', { action: t('telegram.openInWeb') })}
      </Banner>
      <code className="secret">{link.url}</code>
      <p className="max-w-prose text-sm text-muted">
        {t('telegram.codeLine', {
          code: link.code,
          time: formatTime(link.expires_at),
        })}
      </p>
      <p className="max-w-prose text-sm text-muted">
        {t('telegram.notStartBot', {
          action: t('telegram.startBot'),
          site: 'web.telegram.org',
          code: link.code,
        })}
      </p>
      <p className="max-w-prose text-sm text-muted">
        {t('telegram.listenHint')}{' '}
        <code>python main.py telegram listen</code>
      </p>
      <div className="modal-actions">
        <button type="button" className="btn" onClick={onDismiss}>
          {t('generic.done')}
        </button>
      </div>
    </div>
  )
}

function formatTime(value: string | null): string {
  if (!value) return '—'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleTimeString()
}

function message(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback
}
