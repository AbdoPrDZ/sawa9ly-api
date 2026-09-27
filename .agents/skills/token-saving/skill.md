Python Production Token Efficiency
Objective

Minimize agent token usage and context size while maintaining production safety, correctness, and existing behavior.

Core Rules

Inspect narrowly

Do not read the entire repository.

Start with the user's target file, function, class, or error.

Search for relevant symbols/usages before opening additional files.

Only read files required to understand or safely modify the task.

Avoid unnecessary context

Do not load generated files, virtual environments, caches, build artifacts, logs, or dependency source unless explicitly required.

Prefer source files over generated output.

Do not repeatedly read files already inspected.

Do not summarize large files unless the summary is necessary for the task.

Search before reading

For unknown code, search for:

function/class names

imports

API endpoints

configuration keys

tests

callers

Then inspect only the relevant sections.

Make the smallest safe change

Modify only what is necessary.

Do not refactor unrelated code.

Do not rename variables/functions/classes unless required.

Do not reformat unrelated code.

Preserve existing public APIs and behavior unless the task explicitly requires a change.

Production safety has priority

Never sacrifice correctness merely to save tokens.

Preserve error handling, validation, authentication, authorization, transactions, concurrency behavior, and backwards compatibility.

If a broader inspection is necessary for safety, inspect it even if it costs tokens.

Python-Specific Rules
Imports

Prefer existing project dependencies and patterns.

Do not introduce a new dependency when the standard library or an existing dependency is sufficient.

Before adding an import, check whether the dependency already exists in the project.

Types

Follow the project's existing typing style.

Do not add extensive type annotations to unrelated code.

When modifying typed code, preserve type correctness.

Exceptions

Do not broadly replace specific exceptions with Exception.

Do not remove existing exception handling merely to simplify code.

Preserve error semantics.

Async Code

Do not convert synchronous code to async, or async code to synchronous, unless explicitly required.

Preserve existing concurrency behavior.

Database Code

Treat database operations as high-risk.

Before changing queries, transactions, migrations, locking, or connection handling, inspect the relevant callers/tests/configuration.

Do not make speculative database optimizations.

APIs

When modifying an API:

preserve existing response formats unless explicitly requested

preserve status codes

preserve authentication/authorization behavior

preserve validation behavior

inspect relevant tests before changing behavior

Tests

Use targeted verification.

Identify the smallest relevant test set.

Run those tests first.

If they pass and the change is isolated, do not unnecessarily run the entire test suite.

Run broader tests when:

shared infrastructure changed

public interfaces changed

database behavior changed

configuration changed

authentication/authorization changed

the targeted tests cannot provide sufficient confidence

Never skip tests solely to save tokens.

Debugging

Use this order:

Inspect the error.

Locate the failing symbol.

Find its callers.

Inspect the smallest relevant code region.

Check relevant tests/configuration.

Make the minimal fix.

Run targeted verification.

Do not explore unrelated architecture unless evidence requires it.

Context Management

Maintain a compact working context.

After understanding a file, retain only:

relevant functions/classes

important interfaces

dependencies

constraints

test expectations

Do not repeatedly quote or reproduce large sections of code.

When a file is large, inspect only relevant line ranges where possible.

Existing Patterns

Prefer existing project patterns over inventing new abstractions.

Before introducing a helper, utility, class, framework feature, or architectural pattern, search for an existing equivalent.

Reuse established conventions.

Refactoring

Do not perform opportunistic refactoring.

If the requested change can be safely implemented without refactoring, do not refactor.

If refactoring is necessary, keep the scope minimal and verify affected behavior.

Dependency Changes

Do not add packages unless necessary.

Before adding one:

Check existing dependencies.

Check whether the standard library solves the problem.

Check whether an existing project utility already solves it.

Dependency changes require explicit justification.

Output Efficiency

Keep responses concise.

After completing a task, report only:

what changed

files changed

verification performed

any remaining concern

Do not provide long explanations unless requested.

Stop Conditions

Stop investigating when you have enough evidence to:

understand the requested behavior

identify the affected code

make a minimal safe change

verify the change appropriately

Do not continue exploring the repository after the task is sufficiently understood.

Critical Rule

Optimize context, not correctness.

When token savings conflict with production safety, choose production safety.

The goal is:

Read less. Change less. Verify enough. Preserve behavior.