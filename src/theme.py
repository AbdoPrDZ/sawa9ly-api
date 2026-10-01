"""The project's dark palette, named once.

These are the same four values as the `:root` block in
`dashboard/src/styles.css`, and they are here because two hand-written pages need
them: the site root served by `src/server.py`, and the OAuth sign-in page served
by `src/mcp/authorization.py`. Neither page has a stylesheet to inherit from, so
the numbers have to exist on this side too.

They live in their own module rather than in either server because importing
either server is not free: `src/server.py` runs `create_app()` at import, and the
MCP server builds tools and opens the database. A palette cannot be imported from
a process that has side effects.

Changing the palette means changing them here *and* in the dashboard stylesheet.
"""

#: The page background, near-black and slightly blue.
CANVAS = "#0b0d10"
#: Body text.
INK = "#e9ecf1"
#: Secondary text: hints, labels, column headings.
MUTED = "#8b95a4"
#: The brand amber. Filled surfaces use the `solid` variant; this is the one read
#: as text, on the near-black canvas.
ACCENT = "#ffc107"
