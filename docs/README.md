# Documentation

Everything about sawa9ly, split so that each file answers one question. The
[README](../README.md) is the short version: what this is and how to start it.
This is the long version.

## The tree

```
docs/
├── start/                     getting it running
│   ├── README.md              requirements, install, first run, the site account
│   ├── configuration.md       every environment variable, and where files are written
│   └── docker.md              the two compose stacks, and the container layout
│
├── guides/                    doing a thing
│   ├── cli.md                 every command
│   ├── http-api.md            calling the API: credentials, errors, workflows
│   ├── mcp.md                 calling it from an AI agent: keys, tools, checkout
│   ├── dashboard.md           the admin dashboard, and what each role can do
│   ├── pages.md               landing pages, and publishing one
│   ├── tracking.md            watched products, the queue, notifications
│   └── telegram.md            linking a chat, and the listener
│
└── reference/                 looking something up
    ├── routes.md              the route table, and what is unversioned
    ├── python-api.md          the Python package, and checking out with it
    ├── logging.md             the five log files
    ├── project-layout.md      what each file in the repository is for
    ├── site-behaviour.md      how sawa9ly.app really behaves
    ├── caveats.md             known limits, and things that will bite you
    └── security.md            credentials, git, file permissions, rotation
```

## Where to start

| If you want to | Read |
| --- | --- |
| run it on your machine | [start/README.md](start/README.md) |
| run it in containers | [start/docker.md](start/docker.md) |
| know what you can configure | [start/configuration.md](start/configuration.md) |
| drive it from a terminal | [guides/cli.md](guides/cli.md) |
| call it from your own code | [guides/http-api.md](guides/http-api.md) |
| drive it from an AI agent | [guides/mcp.md](guides/mcp.md) |
| find out what broke | [reference/logging.md](reference/logging.md) |
| know what it cannot do | [reference/caveats.md](reference/caveats.md) |

## How this is arranged

**Three parts, and the difference is what you are doing.** `start/` is ordered —
read it in order the first time and it gets you to a working installation.
`guides/` is a task: each file is one thing you might want to do, and you can jump
straight to it. `reference/` is a lookup, and none of it assumes you have read
anything else.

**One question per file.** A file that answers two questions gets read by the
wrong person and maintained by the wrong person, so the split follows the
questions rather than the subject matter. The five subsystems each have their own
log file, and the same reasoning is why logging has a reference page of its own
rather than a section of the configuration page.

**The CLI mirrors the API, and they are documented separately.**
[guides/cli.md](guides/cli.md) and [guides/http-api.md](guides/http-api.md) cover
the same operations from two directions, and a change to one is a change to the
other. [guides/mcp.md](guides/mcp.md) is the third of the three, for an AI agent.
There is one list of routes, in [reference/routes.md](reference/routes.md),
so a route is never described in two places and contradicted in one of them.

## If you are an agent rather than a person

`.agents/context/` holds a separate, more compressed description of the same
codebase, written for an agent starting cold: what each module owns, which
invariants have to hold, and where the code knowingly departs from its own
conventions. It is not documentation for a reader, and it is not a substitute for
these files. `AGENTS.md` says which to read first.
