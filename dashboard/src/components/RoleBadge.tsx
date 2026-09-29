/** The three roles, styled apart so a root account is obvious in a list. */
export function RoleBadge({ role }: { role: string }) {
  return <span className={`badge badge-${role}`}>{role}</span>
}
