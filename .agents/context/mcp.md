# MCP

A third front end, after the CLI and the HTTP API, over the same services.
FastMCP, in `src/mcp/`, served by `python main.py mcp` — which is a command in
`cli/mcp.py` and nothing else: the package builds the server, the command serves
it.

Its own process, on its own port (`MCP_HOST`/`MCP_PORT`, default
`127.0.0.1:8001`), with the streamable-HTTP transport at `MCP_PATH`
(`/mcp/`). Not mounted on the FastAPI app and not under `/api`, for the same
reason the key type is separate: a different credential on a path that is already
published contract would make one restart take both surfaces down.

## Why it is not just another route

An MCP client is a language model, not a script. Three things follow, and they are
the only things that differ from a controller:

- **Authentication is per call.** A shell gets `--user`; a process serving many
  clients gets the key on the request headers. There is no default user and no
  `--user` on `mcp` — the server has no user of its own to be told about.
- **Failures are raised, never returned.** A tool that answered `{"error": ...}`
  would be a *successful* call carrying a failure the model has to notice. See
  `errors.py`, which exists because the refusals that HTTP can express as 404 and
  409 have no equivalent here.
- **The docstring is the interface.** FastMCP derives a tool's input schema from
  its signature and its description from its docstring, so a tool's prose has to
  say what it is *for*. This is why the checkout tools spell out that a
  non-`dry_run` call places an order that cannot be cancelled.

## The credential

`McpAuth` resolves the caller from the key on the current request, and only a key
of type `mcp`. Everything else follows from "the key identifies the user" exactly
as on `/api/v1`: no user in the arguments, one `Livewire` per user, one cart each.

Two library details cost real time and are worth not rediscovering:

- `get_http_headers()` **lowercases every name**. Looking a header up as
  `X-API-Key` returns nothing, and a perfectly valid key reads as absent. The
  constant is `x-api-key` for that reason.
- the same call **strips `authorization`** unless it is named in `include`. Both
  accepted headers are therefore requested explicitly; `cookie` is not, which is
  deliberate — this project has real session cookies and no reason to read them.

`tools/list` is *not* authenticated. Anything that can reach the port sees every
tool name and description; every tool *call* needs a key. That is how MCP servers
normally behave, and the default bind is loopback. Closing it would mean an
`AuthProvider`, which is a deployment story this project does not have yet.

## One divergence from the HTTP API, on purpose

`save_catalogue_product` scrapes through **the caller's own** sawa9ly session.
`/api/v1/catalogue/{id}` scrapes through `User.browsable` — the first user by name
with complete credentials — because that route carries no `Depends` and so knows
no caller. The reasoning inverts here: this call knows whose session it is, so
there is nothing left to borrow one for, and a caller missing their own
credentials is told so by name with the command to fix it rather than being
quietly served by a stranger's session.

The other two catalogue tools are the mirror image of that: the rows belong to no
user, so `list_catalogue` and `get_catalogue_product` call `McpAuth.user()` for no
reason except to require the credential. They do it anyway. A tool surface where
three local-table tools need no key is a surface where nothing does.

## What is and is not a tool

A module exists for every `/api/v1` resource, and **`TOOL_GROUPS` in
`src/mcp/server.py` is the switchboard**: a resource is served when it is in that
tuple and not otherwise. Three are on — products, catalogue, pages, ten tools.
The other six (cart, checkout, clients, orders, telegram, trackers) are written
and commented out, so **the surface does not currently mirror `/api/v1`**.

Turning one on is uncommenting its import and its tuple entry. Nothing else is
missing: the module, `McpAuth` and the per-key ownership scoping are already there.

Cart and orders are the deliberate half to leave off first, because they are the
ones that can spend money. `INSTRUCTIONS` is kept in step with the tuple on
purpose — it is text handed to a language model, and a model told about a tool
that is not registered will ask for it and get "no such tool" rather than being
told plainly that there is none.

The mirroring rule is otherwise unchanged: an operation in one front end and not
the others is unfinished work.

Two things that are HTTP routes are **not** tools whatever the tuple says, for
the reasons `trackers.py` and `telegram.py` state in their own docstrings: the
tracking pass, and polling Telegram. Both are long-lived processes, and one tool
call must not be able to become a loop that outlives it.

## In a container

The `mcp` service in both compose stacks, on the host's loopback at `8001`. The
one image serves it: `command: ["python", "main.py", "mcp"]`.

Two things about it that are not obvious from the service block:

- **It replaces the image's health check rather than disabling it.** The image's
  probe asks for `/docs`, which this container does not serve, so it would report
  permanently unhealthy the way `telegram` and `cron` do. The replacement asserts
  the mount answers a `GET` with **406 Not Acceptable** — the streamable-HTTP
  transport only accepts a JSON-RPC `POST` — and that 406 is the healthy answer.
  It separates three failures a socket check calls identical: refused means the
  server is down, 404 means `MCP_PATH` is wrong. `http.client` rather than
  `urllib`, because urllib raises on a 4xx and inverting that is what keeps the
  probe to one line.
- **`MCP_PUBLISHED_HOST` is not `MCP_HOST`.** The container binds `0.0.0.0`
  because the loopback interface in there is the container's own; the host side
  defaults to `127.0.0.1`. `serve` got `API_PUBLISHED_HOST` for the same reason,
  and the pair is split in both stacks.

## Shape

One module per resource, mirroring `src/controllers/`, each a class whose
`tools()` returns its callables. Every method name is unique across the package
and is the tool's public name — FastMCP keys its registry by name, so two `read`
methods in different resources would be one tool.

`TOOL_GROUPS`, at module level in `src/mcp/server.py`, is that list, written
once. Adding a resource means adding a module and one entry, in the order
`create_app` mounts the corresponding controller — and deciding whether it
should be switched on at all, which is a separate question from whether it works.
