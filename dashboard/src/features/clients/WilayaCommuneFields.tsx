import { useEffect, useState } from 'react'

import { isUnauthorized } from '../../api/client'
import { listCommunes, listWilayas } from '../../api/wilayas'
import type { Commune, Wilaya } from '../../api/types'
import { Field } from '../../components/Field'
import { Banner } from '../../components/Banner'
import { MessageSpinner } from '../../components/Spinner'
import { apiErrorMessage } from '../../i18n/apiError'
import { useI18n } from '../../i18n/useI18n'
import { useSession } from '../../session/useSession'

/** Both ids as the strings the form holds, since an empty box is '' and not 0. */
interface Props {
  wilayaId: string
  communeId: string
  onChange(wilayaId: string, communeId: string): void
}

/**
 * Wilaya and commune as two dropdowns, the second following the first.
 *
 * They were number inputs, which asked whoever was filling in an address to know
 * the site's internal numbering for their own province. The names are the site's
 * own Arabic, and the numbers are still what gets submitted — the selects are a
 * way of choosing an id, not a change to what is stored.
 *
 * **Changing the wilaya clears the commune, and that is the point.** The site
 * decides which communes belong to a wilaya and rejects the order otherwise, so a
 * commune left over from the previous wilaya is a pair that cannot be submitted.
 * Clearing it is the only honest answer, and it is why the commune fetch is keyed
 * on the wilaya rather than run once for the whole country.
 *
 * Both lists are read locally, so the only latency is the database. The wilayas
 * load once on mount; the communes load whenever the wilaya changes, and a stale
 * answer for a wilaya the user has already moved off is dropped rather than shown.
 */
export function WilayaCommuneFields({ wilayaId, communeId, onChange }: Props) {
  const { t } = useI18n()
  const { invalidate } = useSession()

  const [wilayas, setWilayas] = useState<Wilaya[] | null>(null)
  const [communes, setCommunes] = useState<Commune[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let wanted = true

    listWilayas()
      .then((rows) => {
        if (wanted) setWilayas(rows)
      })
      .catch((caught: unknown) => {
        if (!wanted) return
        // A 401 is the session's business, not a message about wilayas: the
        // session clears the token and the app goes back to the login screen.
        if (isUnauthorized(caught)) invalidate()
        else setError(apiErrorMessage(caught, t, 'error.wilayas'))
      })

    return () => {
      wanted = false
    }
  }, [invalidate, t])

  useEffect(() => {
    if (!wilayaId) {
      setCommunes(null)
      return
    }

    let wanted = true

    setCommunes(null)
    listCommunes(Number(wilayaId))
      .then((rows) => {
        if (wanted) setCommunes(rows)
      })
      .catch((caught: unknown) => {
        if (!wanted) return

        if (isUnauthorized(caught)) invalidate()
        else setError(apiErrorMessage(caught, t, 'error.communes'))
      })

    return () => {
      wanted = false
    }
  }, [wilayaId, invalidate, t])

  function onWilaya(next: string) {
    // The commune goes with the wilaya it belonged to. See the note above.
    onChange(next, '')
  }

  return (
    <>
      {error ? <Banner kind="error">{error}</Banner> : null}

      <Field label={t('client.fieldWilaya')} hint={t('client.fieldWilayaHint')}>
        {wilayas === null ? (
          <MessageSpinner messageKey="loading.wilayas" />
        ) : (
          <select value={wilayaId} onChange={(event) => onWilaya(event.target.value)}>
            <option value="">{t('client.pickWilaya')}</option>
            {wilayas.map((wilaya) => (
              <option key={wilaya.id} value={wilaya.id}>
                {wilaya.number ? `${wilaya.number} - ${wilaya.name}` : wilaya.name}
              </option>
            ))}
          </select>
        )}
      </Field>

      <Field label={t('client.fieldCommune')} hint={t('client.fieldCommuneHint')}>
        <select
          value={communeId}
          // Disabled until a wilaya is chosen, because there is no list to offer
          // before that and an empty dropdown that can be opened and finds nothing
          // in it reads as a fault rather than as "pick a wilaya first".
          disabled={!wilayaId || communes === null}
          onChange={(event) => onChange(wilayaId, event.target.value)}
        >
          <option value="">
            {wilayaId
              ? communes === null
                ? t('loading.communes')
                : t('client.pickCommune')
              : t('client.pickWilayaFirst')}
          </option>
          {(communes ?? []).map((commune) => (
            <option key={commune.id} value={commune.id}>
              {commune.name}
            </option>
          ))}
        </select>
      </Field>
    </>
  )
}