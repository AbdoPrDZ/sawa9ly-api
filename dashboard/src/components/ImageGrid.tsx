/** A grid of clickable image thumbnails.
 *
 * Each thumbnail is a button rather than a bare image, because it is only ever
 * a way to ask for the whole picture — the same reason a row's "Open" is a link
 * and not a decoration. The caller owns what opening one means and how a
 * thumbnail is announced; this only lays them out.
 */
export function ImageGrid({
  urls,
  label,
  onSelect,
}: {
  urls: string[]
  label(position: number, total: number): string
  onSelect(url: string): void
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
      {urls.map((url, position) => (
        <button
          key={url}
          type="button"
          onClick={() => onSelect(url)}
          aria-label={label(position + 1, urls.length)}
          className="group overflow-hidden rounded-lg border border-line bg-surface transition-[border-color,transform] duration-150 hover:-translate-y-0.5 hover:border-line-strong"
        >
          <img
            src={url}
            alt=""
            loading="lazy"
            className="aspect-square w-full object-cover transition-opacity duration-200 group-hover:opacity-80"
          />
        </button>
      ))}
    </div>
  )
}
