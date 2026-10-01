import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { getProfile, sawa9lyLogin, updateProfile } from '../api/profile'
import type { Locale, Profile, ProfileIn } from '../api/types'
import { Banner } from '../components/Banner'
import { Field } from '../components/Field'
import { PageHeader } from '../components/PageHeader'
import { RoleBadge } from '../components/RoleBadge'
import { MessageSpinner } from '../components/Spinner'
import { apiErrorMessage } from '../i18n/apiError'
import { useI18n } from '../i18n/useI18n'
import { TelegramCard } from '../features/telegram/TelegramCard'

/** A user's own account.
 *
 * Available to every signed-in user, whatever their role: changing your own
 * password, your own sawa9ly credentials, your language or your own Telegram
 * chat should never need an administrator. Nobody can set these for you, which
 * is why they are all on this page and none of them are on anyone else's.
 *
 * Each of the four is a card, because each is a form that is submitted on its own
 * and saves on its own — grouping them into one panel would suggest they are
 * saved together.
 */
export function ProfilePage() {
  const { t, locale, languageNames, locales, setLocale, savingLocale } = useI18n()

  const [profile, setProfile] = useState<Profile | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [loggingIn, setLoggingIn] = useState(false)

  const [email, setEmail] = useState('')
  const [sawa9lyPassword, setSawa9lyPassword] = useState('')
  const [dashboardPassword, setDashboardPassword] = useState('')

  const load = useCallback(async () => {
    try {
      const loaded = await getProfile()
      setProfile(loaded)
      setEmail(loaded.sawa9ly_email ?? '')
    } catch (caught) {
      setError(apiErrorMessage(caught, t, 'error.profile'))
    }
    // `t` is stable for a given locale, and the profile is loaded once per
    // language rather than once per render.
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  if (!profile) return <MessageSpinner messageKey="loading.profile" />

  async function save(event: FormEvent) {
    event.preventDefault()
    setError('')
    setNotice('')
    setBusy(true)

    // Only the fields that were actually filled in. An empty box means
    // "leave it alone"; clearing a credential is done explicitly below.
    const input: Partial<ProfileIn> = {}

    if (email !== (profile?.sawa9ly_email ?? '')) input.sawa9ly_email = email
    if (sawa9lyPassword) input.sawa9ly_password = sawa9lyPassword
    if (dashboardPassword) input.password = dashboardPassword

    if (Object.keys(input).length === 0) {
      setNotice(t('profile.nothingToSave'))
      setBusy(false)
      return
    }

    try {
      const updated = await updateProfile(input)
      setProfile(updated)
      setEmail(updated.sawa9ly_email ?? '')
      setSawa9lyPassword('')
      setDashboardPassword('')
      setNotice(t('profile.saved'))
    } catch (caught) {
      setError(apiErrorMessage(caught, t, 'error.profile'))
    } finally {
      setBusy(false)
    }
  }

  async function onSawa9lyLogin() {
    setError('')
    setNotice('')
    setLoggingIn(true)

    try {
      const result = await sawa9lyLogin()
      setNotice(result.message)
      await load()
    } catch (caught) {
      setError(apiErrorMessage(caught, t, 'error.profile'))
    } finally {
      setLoggingIn(false)
    }
  }

  /**
   * Save the language.
   *
   * Delegates entirely to the provider, which also backs it out if the server
   * refuses. This page used to do the `PATCH` and the session refresh itself,
   * which meant two places to keep in step — and two copies of the revert — once
   * the top bar could switch the language too.
   */
  function onLocaleChange(next: Locale) {
    setLocale(next)
  }

  return (
    <section>
      <PageHeader title={t('profile.title')}>
        <RoleBadge role={profile.role} />
      </PageHeader>

      {error ? <Banner kind="error">{error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="card">
          <h3 className="mb-3">{t('profile.language')}</h3>
          <label className="block">
            <span className="sr-only">{t('profile.language')}</span>
            <select
              value={locale}
              disabled={savingLocale}
              onChange={(event) => void onLocaleChange(event.target.value as Locale)}
            >
              {locales.map((option) => (
                <option key={option} value={option}>
                  {languageNames[option]}
                </option>
              ))}
            </select>
          </label>
          <p className="mt-3 text-xs text-muted">{t('profile.languageHint')}</p>
        </div>

        <div className="card">
          <h3 className="mb-2">{t('profile.sawa9ly')}</h3>
          <p className="mb-3 text-sm text-muted">
            {profile.has_sawa9ly_credentials
              ? t('profile.sawa9lyHas')
              : t('profile.sawa9lyHasNot')}
          </p>
          <p className="mb-4 text-sm">
            {t('profile.siteSession')}{' '}
            {profile.has_sawa9ly_session ? (
              <span className="badge badge-ok">{t('profile.sessionReady')}</span>
            ) : (
              <span className="badge badge-warn">{t('profile.sessionNone')}</span>
            )}
          </p>
          <button
            type="button"
            className="btn btn-primary"
            disabled={loggingIn || !profile.has_sawa9ly_credentials}
            title={
              profile.has_sawa9ly_credentials ? undefined : t('profile.logInNeedsCredentials')
            }
            onClick={onSawa9lyLogin}
          >
            {loggingIn ? t('profile.logInBusy') : t('profile.logIn')}
          </button>
        </div>

        <form className="card" onSubmit={save}>
          <h3 className="mb-4">{t('profile.changeDetails')}</h3>

          <Field label={t('profile.fieldEmail')} hint={t('profile.fieldEmailHint')}>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="off"
            />
          </Field>

          <Field
            label={t('profile.fieldSawa9lyPassword')}
            hint={t('profile.fieldSawa9lyPasswordHint')}
          >
            <input
              type="password"
              value={sawa9lyPassword}
              onChange={(event) => setSawa9lyPassword(event.target.value)}
              autoComplete="new-password"
            />
          </Field>

          <Field
            label={t('profile.fieldDashboardPassword')}
            hint={t('profile.fieldDashboardPasswordHint')}
          >
            <input
              type="password"
              value={dashboardPassword}
              onChange={(event) => setDashboardPassword(event.target.value)}
              autoComplete="new-password"
            />
          </Field>

          <div className="mt-1 flex justify-end">
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? t('profile.busy') : t('profile.saveChanges')}
            </button>
          </div>
        </form>

        <TelegramCard />
      </div>
    </section>
  )
}

