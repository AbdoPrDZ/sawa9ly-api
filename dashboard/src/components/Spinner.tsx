/** Placeholder while a page's data is in flight. */
export function Spinner({ label }: { label: string }) {
  return <p className="muted">{label}…</p>
}