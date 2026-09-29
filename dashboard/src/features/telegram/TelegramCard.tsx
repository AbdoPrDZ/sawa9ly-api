import { useCallback, useEffect, useState } from 'react'
import { getBinding, issueLink, sendTest, unbind } from '../../api/telegram'
import type { TelegramBinding, TelegramLink } from '../../api/types'
import { Banner } from '../../components/Banner'
import { Spinner } from '../../components/Spinner'

/** Linking this user's account to a Telegram chat.
 *
 * The link is shown once and then forgotten, because the code in it is stored
 * only as a hash — the same contract an API key has. Losing it is not a problem:
 * "Get a new link" makes a new one, and issuing one does not unbind the chat the
 * user already had.
 */
export function TelegramCard() {
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
      setError(message(caught, 'Could not read your Telegram link.'))
    }
  }, [])

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
      setError(message(caught, 'Could not make a link. Is TELEGRAM_BOT_TOKEN set?'))
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
      setError(message(caught, 'Could not unlink your chat.'))
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
      setNotice('Sent. Check the chat.')
    } catch (caught) {
      setError(message(caught, 'Could not send the test message.'))
    } finally {
      setTesting(false)
    }
  }

  if (!binding) return <Spinner label="Loading your Telegram link" />

  return (
    <div className="card">
      <h3>Telegram notifications</h3>

      {error ? <Banner kind="error">{error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      {binding.bound ? (
        <>
          <p className="muted">
            Notifications go to{' '}
            <strong>{binding.chat_title ?? binding.chat_username ?? binding.chat_id}</strong>{' '}
            ({binding.chat_type}).
          </p>
          <div className="modal-actions">
            {/* Real notifications are not wired up yet, so this is the only way
                to find out that a linked chat actually delivers. */}
            <button type="button" className="ghost" disabled={testing} onClick={onTest}>
              {testing ? 'Sending…' : 'Send a test message'}
            </button>
            <button type="button" className="ghost" disabled={busy} onClick={onUnbind}>
              Unlink this chat
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="muted">
            Link a private chat with the bot, and it will be where your notifications
            arrive. A private channel you own works too, with the bot added as an
            admin.
          </p>
          {binding.code_pending ? (
            <p>
              Waiting for you to open the link.{' '}
              <span className="badge">expires {formatTime(binding.code_expires_at)}</span>
            </p>
          ) : null}
          <button type="button" className="primary" disabled={busy} onClick={getLink}>
            {busy ? 'Working…' : binding.code_pending ? 'Get a new link' : 'Get a link'}
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
 *  fails. "Start Bot" hands off to Telegram's app through the `tg://` scheme,
 *  which a browser reports as *"scheme does not have a registered handler"* on a
 *  computer with no Telegram app installed — the button then does nothing at all,
 *  silently. "Open in Web" carries the same code in a `tgaddr` fragment and works
 *  with no app, so the instruction names it rather than saying "open this link".
 *
 *  The code is offered alongside for the same reason: it works in every client,
 *  installed or not.
 */
function LinkPanel({ link, onDismiss }: { link: TelegramLink; onDismiss(): void }) {
  return (
    <div className="link-panel">
      <Banner kind="info">
        Open this link, then press <strong>Open in Web</strong> on the page that
        comes up. It is shown once and cannot be recovered.
      </Banner>
      <code className="copyable">{link.url}</code>
      <p className="muted">
        Code <strong>{link.code}</strong>, good until {formatTime(link.expires_at)}. It stops
        working once used, or when it expires.
      </p>
      <p className="muted">
        Do not press <strong>Start Bot</strong> — that one needs Telegram installed on this
        computer, and does nothing at all without it. <strong>Open in Web</strong> works
        either way. If you would rather not use the link, open the bot in the Telegram app
        or at <strong>web.telegram.org</strong> and send <strong>{link.code}</strong> as a
        message.
      </p>
      <p className="muted">
        Nothing arrives until <code>python main.py telegram listen</code> is running — that is
        what receives the message.
      </p>
      <div className="modal-actions">
        <button type="button" className="ghost" onClick={onDismiss}>
          Done
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
