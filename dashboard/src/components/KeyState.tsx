/** Why a key does or does not still work. Three states, not two, because
 * "expired" and "revoked" need different reactions.
 */
export function KeyState({ revoked, usable }: { revoked: boolean; usable: boolean }) {
  if (revoked) return <span className="badge badge-revoked">revoked</span>
  if (!usable) return <span className="badge badge-expired">expired</span>
  return <span className="badge badge-active">active</span>
}