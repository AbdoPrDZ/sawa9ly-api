import { Banner } from '../../components/Banner'
import { Modal } from '../../components/Modal'

/** Shows a key's plaintext exactly once.
 *
 * The server keeps only a hash, so this cannot be shown again. Copying is
 * best-effort: clipboard access needs a secure context and may be refused.
 */
export function RevealKeyModal({ secret, onClose }: { secret: string; onClose(): void }) {
  return (
    <Modal title="Copy this key now" onClose={onClose}>
      <Banner kind="info">
        This is the only time the key is shown. The server keeps only a hash, so it cannot be
        shown again — if you lose it, issue a new one.
      </Banner>

      <pre className="key-box">{secret}</pre>

      <div className="modal-actions">
        <button
          type="button"
          className="ghost"
          onClick={() => navigator.clipboard?.writeText(secret)}
        >
          Copy
        </button>
        <button type="button" className="primary" onClick={onClose}>
          Done
        </button>
      </div>
    </Modal>
  )
}