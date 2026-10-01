import type { AdminUser } from '../../api/types'
import { Modal } from '../../components/Modal'
import { useI18n } from '../../i18n/useI18n'

/** Confirms a delete, which cascades to keys, clients and orders. */
export function DeleteUserModal({
  user,
  onCancel,
  onConfirm,
}: {
  user: AdminUser
  onCancel(): void
  onConfirm(): void
}) {
  const { t } = useI18n()

  return (
    <Modal title={t('user.deleteTitle', { name: user.username })} onClose={onCancel}>
      <p className="text-sm">{t('user.deleteBody')}</p>
      <div className="modal-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          {t('generic.cancel')}
        </button>
        <button type="button" className="btn btn-danger" onClick={onConfirm}>
          {t('user.deleteConfirm')}
        </button>
      </div>
    </Modal>
  )
}
