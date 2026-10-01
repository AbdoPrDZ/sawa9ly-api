import { Banner } from '../../components/Banner'
import { Modal } from '../../components/Modal'
import { useI18n } from '../../i18n/useI18n'

/** Shows a key's plaintext exactly once.
 *
 * The server keeps only a hash, so this cannot be shown again. Copying is
 * best-effort: clipboard access needs a secure context and may be refused.
 */
export function RevealKeyModal({ secret, onClose }: { secret: string; onClose(): void }) {
  const { t } = useI18n()

  return (
    <Modal title={t('key.revealTitle')} onClose={onClose}>
      <Banner kind="info">{t('key.revealBanner')}</Banner>

      <pre className="secret">{secret}</pre>

      <div className="modal-actions">
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => navigator.clipboard?.writeText(secret)}
        >
          {t('generic.copy')}
        </button>
        <button type="button" className="btn btn-primary" onClick={onClose}>
          {t('generic.done')}
        </button>
      </div>
    </Modal>
  )
}