# AGENTS.md

Rules for working in this repository. Obey them when writing or changing code
here.

Project knowledge — architecture, the data model, the API surface, the site's
behaviour — lives in `.agents/context/`. This file is rules only. Do not grow it
with descriptions of how the project works; those belong in the context.

## Project context

Before substantial work, read:

```text
.agents/context/README.md → config.md → structure.md → the relevant files
```

`structure.md` says which file owns which knowledge, and the context README says
what to read per task type. Read what your task touches, not everything.

- **Context is derived knowledge, not authority.** If it disagrees with the code,
  the code is right: correct the context and carry on. Never edit source to match
  stale context.
- **Keep it updated.** The configured mode is `automatic`: after a change that
  alters what another agent needs to know — a new module, route, entity, workflow,
  integration, or a changed convention — update the affected context files, check
  them against the source, and say what you updated.
- **Do not update for** formatting, renames, small refactors, plain bug fixes or
  scratch scripts. That churn makes the context untrustworthy.
- **Update only the affected files.** One new endpoint is one file touched, not a
  rewrite of the context.
- Level-scale reference: `structure.md` (per-level file sets) and `config.md`
  (what the current settings mean).

## Ask before adding

**Build what was asked for, and nothing else.** Do not introduce a model, a
table, a column, a route, a command, a dependency, a setting or a "helpful"
convenience that was not requested — however obviously it seems to be needed,
and however much better the result would be.

If you notice a bug, a gap, a missing case or an improvement, **say so and wait**.
One sentence is enough: *"there is no record of what changed — want a table for
that, or is the current state enough?"* Then stop and let the answer decide.

The reasoning: every extra thing is a thing to maintain, migrate, document and
reason about, and the person who has to live with it is not you. An
unrequested addition is not a gift, it is a decision taken away.

If something is genuinely required to make the requested thing work, that is not
an addition — but say which part you added and why, in the summary.

Corollary: do not "improve" behaviour that was not in scope, even where the
current behaviour looks wrong. Report it instead.

## Classes everywhere

**No new module-level functions.** Group behaviour into classes:

- a `staticmethod` or `classmethod` for a named operation on a type;
- a namespaced class (`Dependencies`) for helpers that belong to no one entity;
- a class that owns the data — lookups as classmethods, behaviour as instance
  methods.

Reach for a class before writing a bare `def`. Some modules predate this rule and
still have module-level functions; `conventions.md` lists them. Treat those as
grandfathered — do not add to them, and do not move one as a side effect of
unrelated work.

## Adding features

The API mirrors the CLI. A new operation means a method on a service, a schema if
it has a body, a controller handler, a CLI command, and a router include if the
controller is new. Any subset of that is unfinished work.

`conventions.md` records the pattern each layer follows.

## One thing per file

**A file holds one thing. When a second thing arrives, it gets its own file.**

This is the project's style, and it applies to every language in it — Python,
TypeScript, CSS. Do not park two services, two resources or a grab-bag of
components in one module because they are related or because splitting felt like
fussiness.

Split when a file gains:

- **a second class that is not a subclass or a helper of the first** — `Passwords`
  and `Token` are two services, so they are two modules;
- **a second resource** — users and API keys are two things to manage, so they
  are two controllers even when they share the `/admin` prefix;
- **a second component** — one React component per file, not a `ui.tsx` of
  everything small;
- **a second kind of thing that would need its own name** — a types module, a
  transport module and a per-resource API module are three files.

Corollary: do not add to a file merely because it is convenient or already
imported. Growing a file is how a module ends up with two reasons to change.

The exception is a genuinely cohesive unit that is meaningless apart — a single
entity with its lookups, a single component with its own styles, a test and its
fixtures. If you cannot name the file's one responsibility in a few words, it is
probably two files.

## Style

- Two-space indentation (see `.editorconfig`).
- Follow the file's existing quote style; double quotes in ORM entities and
  schemas.
- Docstrings on classes and on any method whose behaviour is not obvious from its
  name. Explain *why* when it is not obvious.
- Comments for what code cannot say. Delete any comment that restates the next
  line.
- Prefer explicit imports of the specific module over a barrel that re-exports
  everything, so a reader can see which file a name actually lives in.

## Testing against the live site

There is no test suite; verification is manual against the real site.

- **Never place a real order.** Use `dry_run=True`, or submit with the required
  client fields omitted so the site rejects it in `errors`. A real order cannot be
  cancelled from here.
- **Leave the cart as you found it.** Quantities persist server-side, so put them
  back; prices never persist, so there is nothing to restore there.
- If a selector stops matching, re-probe the page before "fixing" it. Some are
  only correct for a specific cart or product ordering.

## Selectors

- Prefer an id or a `wire:click` / `wire:model` binding over a Tailwind class
  chain. Bindings are semantic and survive a theme change.
- **Scope by the entity id, never by position.** `div:nth-child(1)` silently
  returns whichever row is first, which is the wrong product as soon as the
  ordering changes.
- Escape `:` and `.` in attribute names: `[wire\\:model\\.live="products_quantity.5663"]`.
- A selector returning an element with no `wire:click` is matching the wrong
  thing. Check what a broad selector actually matched.

## Errors

- Raise, never swallow. `LivewireError` in the client layer, `HTTPException` in
  controllers, a non-zero exit with `error: ...` from the CLI.
- Say what to do next. "Login failed" is useless; "Login failed: the site
  rejected the credentials (check the user's email and password)" is actionable.
- Distinguish "you asked for something impossible" (409) from "the site broke"
  (502).

## Database

- Go through `session_scope()` and the entity classmethods. No ad-hoc SQL, and no
  query string built from user input.
- Keep the SQLite `foreign_keys` pragma on, or `ON DELETE CASCADE` silently does
  nothing and deleting a user orphans everything it owns.
- Sessions and per-user settings live in the database (`data/sawa9ly.db`). Do not
  reintroduce file-based storage.
- Schema is applied with `create_all`, which does not migrate an existing file.
  After a column change, delete the database or add a real migration.

## Concurrency

- `requests.Session` — and therefore a `Livewire` client — is **not
  thread-safe**. FastAPI runs sync handlers on a threadpool, so two requests for
  one user can drive the same session at once. Keep per-user clients and do not
  assume a request is the only one in flight for that user.
- Declare handlers doing blocking I/O as `def`, not `async def`.

## API

- Keep response shapes as declared in `src/schemas.py`; clients depend on them.
  Widen with an optional field rather than renaming or removing one.
- Only the hash of an API key is ever stored. The plaintext is returned once at
  creation and never logged, echoed or written anywhere.

## Security

- Never commit `.env` or `data/`.
- Do not print session cookies or API keys into logs. `main.py login` printing the
  cookie is the one deliberate exception.
- Cookies are credentials. Anything that writes one to disk, a log, or an error
  message is a bug.
