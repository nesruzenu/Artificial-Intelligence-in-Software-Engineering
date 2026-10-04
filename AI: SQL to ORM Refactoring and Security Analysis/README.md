# Task 0: AI Pair Programming — TaskQueue Audit & Refactor

A structured, AI-assisted audit of a JavaScript `TaskQueue` class for Single
Responsibility Principle (SRP) violations and scope/closure bugs, followed by
a refactor and independent verification.

## Files

| File | Description |
|---|---|
| [`task_queue_legacy.js`](./task_queue_legacy.js) | The original flawed class. Mixes five responsibilities into `addTask` and contains a real closure bug (`notify()` closes over an undeclared `name` identifier instead of `this.queueName`). Throws `ReferenceError: name is not defined` when run in Node. |
| [`task_queue_clean.js`](./task_queue_clean.js) | The refactored, implemented version. `addTask` is reduced to validation + array mutation; logging and scheduling are extracted into `TaskQueueLogger` and `QueueScheduler` collaborators; the closure bug is replaced with a pure `isHighPriority()` helper. |

## The Bug (Confirmed, Not Assumed)

The legacy code's `notify()` function references a bare `name` identifier
that is never declared in `addTask`, never passed as a parameter, and is
**not** `this.queueName`:

```javascript
function notify() {
    if (priority > 9) {
        console.warn(`High priority task added to ${name}.`); // 'name' is undeclared here
    }
}
```

In a browser this silently resolves to the `window.name` global (almost
certainly not what was intended). In Node's module scope there is no such
global, so it throws:

```
ReferenceError: name is not defined
    at notify (task_queue_legacy.js:22:50)
    at TaskQueue.addTask (task_queue_legacy.js:25:3)
```

This was verified by actually running the file — not just inferred from
reading the code.

## Prompts Used

### Prompt 1 — Audit (Scope & Closures)

> Request Code Analysis: Here is a JavaScript method, `addTask`, from a
> `TaskQueue` class [code pasted]. Please analyze it for scope and closure
> issues.
> 1. Trace exactly which variables the inner `notify` function closes over,
>    and where each one comes from (constructor arg, method param, or outer
>    scope).
> 2. Identify any variables here that should be block-scoped (`let`/`const`)
>    but currently aren't, or that rely on ambiguous/global scope, and
>    explain concretely why that's risky.
> 3. Walk me through, step by step, how the closure is formed each time
>    `addTask` runs.

### Prompt 2 — Refactoring (Single Responsibility Principle)

> Focusing only on the Single Responsibility Principle: list every distinct
> responsibility currently living inside `addTask` (I count at least: input
> validation, mutating state, first-task detection/scheduling, console
> logging, and priority-based warning).
>
> Then refactor the class so `addTask` does nothing but validate and push
> the task onto `this.tasks`. Extract the logging and "start processing on
> first task" scheduling into a separate class or function.
>
> After the refactor, explain specifically why it's now easier to unit test
> and maintain.

### Prompt 3 — Final Verification

> Here is my implemented `task_queue_clean.js` file [code pasted]. Compare
> it against the original `task_queue_legacy.js`. Confirm specifically:
> 1. Has the `notify()` closure bug (the unbound `name` reference) been
>    fully resolved, with all variables now either explicit parameters or
>    properly scoped?
> 2. Does `addTask` now have exactly one responsibility (validate + add),
>    with logging and scheduling fully extracted?
> 3. Is the original public behavior preserved — a task still gets pushed,
>    `_startProcessing()` still fires on the first task, and the
>    high-priority warning still fires above the same threshold?
> 4. Flag anything you'd still consider a code smell or something you'd
>    change with more time.

## Critique (Quality / Fit / Understanding / Correctness)

- **Quality** — Clear collaborator names (`TaskQueueLogger`,
  `QueueScheduler`), narrow public methods, and the magic number `9` pulled
  into a named `HIGH_PRIORITY_THRESHOLD` constant.
- **Fit** — No over-engineering (no event bus, no DI container) for a
  ~15-line class; plain constructor-injected collaborators are the right
  size of solution here.
- **Understanding** — Traced the wiring by hand: `QueueScheduler` holds a
  back-reference to its `TaskQueue` (`this.scheduler = new
  QueueScheduler(this)`), passed before the constructor finishes
  initializing `this.tasks`/`this.logger`. This is safe only because
  `maybeStart()` isn't invoked until `addTask()` runs later, by which point
  construction has completed.
- **Correctness** — Verified by execution, not inspection: the legacy file
  throws in Node; the refactored file runs cleanly, pushes tasks correctly,
  triggers `_startProcessing()` on the first task, and fires the
  high-priority warning only above the same threshold as before.

## Reflection

LLMs are pattern-matching engines, not code executors, which means their
confidence in an explanation isn't proof it's correct — I only knew the
`notify()` closure bug was a real, breaking issue (not just a style nit)
after actually running the legacy file in Node and watching it throw
`ReferenceError: name is not defined`. Asking the AI to audit for
structural problems (SRP, closures) rather than just "fix it" forced it to
articulate *why* each piece was wrong — which variables closed over what,
which responsibility belonged to which collaborator — turning the exercise
into something I could verify and learn from, instead of a black-box diff
I'd have to trust blindly.

That distinction is exactly what a linter can't give you: ESLint would
never have flagged `notify()` as a design smell, only a human- or
AI-guided audit reasoning about intent versus scope could catch it. The
AI's pattern-matching was most valuable when aimed at *explaining*
structure rather than silently rewriting it — that's what made the output
something I could critique, verify by execution, and actually learn from.
