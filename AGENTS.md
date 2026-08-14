# US Local Channel Listing Tracker — Project Rules

## Scope and source of truth

- This project is **US Local Channel Listing Tracker**. `Listing Monitor` and `Review Tracker` are modules of one project, not separate projects.
- `config/listing_master.xlsx` is the unified product configuration source. Each row is one platform Listing; it must not contain invented Listings.
- `record_id` is the cross-module relationship key. Use `PLATFORM_INTERNALSKU` when it is stable; do not reuse a `record_id` across platforms.
- `listing_url` is the product-detail-page access anchor. Platform code belongs in `platforms/<platform>/`; common capabilities belong in `shared/`.
- Browser session/profile, database access, matching, evidence, logging, retry/error states, and notification are shared services. Do not copy a browser startup implementation into each module.

## Collection safety and integrity

- Do not bypass access controls, rotate proxies, spoof fingerprints, solve CAPTCHA automatically, use multiple accounts to evade controls, or call non-public APIs.
- If data is not visible, record an explicit unavailable or error state. Never infer a hidden rank or present yesterday's data as today's data.
- A first successful collection establishes a baseline only. Changes require a later comparable snapshot.
- No full collection run, scheduler, or automation may be introduced without approval. Phase 0 creates no production collection records.
- Preserve review history, prior reports, raw inputs, and evidence. Migration proposals must be approved before data movement, rewriting, or deletion.

## Platform constraints

- Walmart: stop on CAPTCHA/Robot Check; do not infer search rank when result cards are absent.
- Lowe's: fixed ZIP, logged-out session, default sort only; retain raw slot and organic whole-machine rank with evidence.
- Home Depot: use the primary product grid only; exclude recommendation modules and retain region/store conditions.

See `docs/platform_collection_rules.md` for the operative rules and `docs/data_dictionary.md` for field definitions.

<!-- BEGIN WEEKLY REVIEW CONTROLLED WORKFLOW -->

# Weekly Review Analysis ? Controlled Agent Workflow

## Project purpose

This project contains cross-channel operational data pipelines, listing trackers, browser-assisted observations, reports, historical outputs, configuration, and automation-related assets for Walmart, THD, Lowe's, and related workflows.

Incorrect execution can alter formal history, latest outputs, operational scope, scheduled runs, or external notifications. Treat state transitions and data writes as controlled operations.

## Source-of-truth rule

Before acting, identify and read the relevant authoritative sources, including existing configuration, policies, schemas, approved scope files, prior successful reports, and current runtime state.

Do not replace existing policy with assumptions written in a prompt.

When configuration and documentation conflict:
- Stop.
- Identify the conflict.
- Cite both sources.
- Ask the parent to resolve it.

## Conditional agent routing

Use one primary agent by default.

The primary agent should normally:
1. Locate the most relevant existing files and current status.
2. Determine the smallest necessary change.
3. Implement the bounded change directly.
4. Run targeted validation.
5. Report the main result, validation, risks, and next action.

Use `data_explorer` only when:
- exploration spans many files or independent data sources;
- search, logs, or intermediate evidence would substantially pollute the main context;
- multiple independent read-only investigations can run in parallel;
- the parent explicitly requests separate evidence gathering.

Use `pipeline_worker` only when:
- the implementation scope is already clear;
- allowed and protected files are explicitly identified;
- acceptance criteria are objective;
- delegating implementation provides a meaningful speed or context benefit.

The primary agent may implement ordinary bounded changes directly. Do not create a worker merely because one is available.

Use `regression_reviewer` only for high-risk changes involving one or more of:
- formal History or outputs/latest;
- financial or SKU aggregation;
- schema or mapping changes;
- state transitions or readiness statuses;
- idempotency, locking, retries, or recovery;
- browser automation, ZIP, account identity, or access handling;
- automation or scheduled execution;
- material expansion of platform, listing, SKU, keyword, or monitoring scope.

For normal low-risk edits, targeted tests and the primary agent's diff review are sufficient.

When subagents are used:
- prefer read-only parallel work;
- do not allow write agents to modify overlapping files;
- the primary agent remains responsible for reviewing evidence, diffs, tests, and final acceptance;
- subagent availability must not expand task scope.

Do not delegate ambiguous architecture, business-policy decisions, financial definitions, SKU-scope decisions, or production authorization to a worker.

## Approval gates

The following require explicit user approval in the current conversation or task:

- Writing formal History.
- Overwriting or promoting to outputs/latest.
- Replacing a successful baseline.
- Running a formal weekly pipeline.
- Starting supervised daily production runs.
- Expanding approved platform, listing, SKU, keyword, ZIP, or monitoring scope.
- Creating, enabling, modifying, disabling, or deleting scheduled tasks or automations.
- Sending Feishu cards, emails, alerts, API writes, or other external notifications.
- Changing production schemas, mapping rules, credentials, browser identities, or database structures.
- Changing retry, timeout, locking, or anti-block policy.
- Deleting or migrating production data.

Statuses such as READY_FOR_PIPELINE, READY_FOR_SECOND_OBSERVATION, READY_FOR_SUPERVISED_DAILY_RUNS, READY_FOR_USER_APPROVAL, or similar readiness labels are handoff states, not authorization.

## Data integrity controls

- Never infer unseen data.
- Never silently convert missing, blank, unavailable, or failed-source data to zero.
- Never silently discard unknown, unmatched, duplicate, or out-of-scope SKUs.
- Preserve exact source dates, run IDs, platform identity, ZIP context, and scope.
- Keep test, preflight, observation, baseline, and formal outputs separate.
- Preserve historical records and successful prior outputs.
- Validate date intervals and current-versus-previous-successful comparisons.
- Reconcile financial totals and SKU-level totals when the task touches sales, refunds, advertising, inventory, or fees.
- Report partial coverage explicitly.

## Browser and access controls

- Do not bypass CAPTCHA, Robot Check, ACCESS_BLOCKED, account identity restrictions, ZIP validation, or platform security.
- Do not retry prohibited failures.
- Preserve approved browser profiles and platform separation.
- Do not change the active ZIP or account identity without authorization.
- Do not write ranking or listing snapshots when required validation has failed.
- Screenshots and evidence must correspond to the same run, platform, profile, ZIP, query, and listing being reported.

## Change controls

Before editing:
- Report current status.
- Report exact files expected to change.
- Report protected files and outputs.
- Report validation plan.

After editing:
- Review the full diff.
- Run relevant non-production tests.
- Confirm that formal History, outputs/latest, scheduler state, approved scope, and external systems remain unchanged.
- Report changed files, test results, reconciliations, residual risks, and blockers.

## Completion language

Do not report READY, SUCCESS, APPROVED, PRODUCTION-READY, or equivalent unless all required checks for that exact status have passed.

When blocked, report:
- exact blocker;
- evidence;
- affected scope;
- what was not changed;
- the next decision required from the user.

<!-- END WEEKLY REVIEW CONTROLLED WORKFLOW -->
