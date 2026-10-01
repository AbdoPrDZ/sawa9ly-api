import type { AdminApiKey } from '../../api/types'
import { Modal } from '../../components/Modal'
import { useI18n } from '../../i18n/useI18n'

/** Confirms a revoke, which takes effect on the key's next use. */
export function RevokeKeyModal({
  apiKey,
  onCancel,
  onConfirm,
}: {
  apiKey: AdminApiKey
  onCancel(): void
  onConfirm(): void
}) {
  const { t } = useI18n()

  return (
    <Modal title={t('key.revokeTitle', { prefix: apiKey.prefix })} onClose={onCancel}>
      <p className="text-sm">{t('key.revokeBody')}</p>
      <div className="modal-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          {t('generic.cancel')}
        </button>
        <button type="button" className="btn btn-danger" onClick={onConfirm}>
          {t('key.revokeConfirm')}
        </button>
      </div>
    </Modal>
  )
}
