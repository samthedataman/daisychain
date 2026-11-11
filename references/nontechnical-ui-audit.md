# Nontechnical UI audit checklist

Use this checklist when reviewing product workflows for nontechnical users.

## Inspect the workflow

Identify routes, navigation, modal entry points, and the empty, loading, error, disabled, and success states. Grade the user's workflow rather than individual source files. Assess mobile behavior where relevant.

- What is the one job the user came here to do?
- Is the first visible action the right action?
- Are primary actions competing with each other?
- Does the screen introduce unexplained jargon?
- Are advanced controls shown only when useful?
- Does an empty state offer an actionable next step?
- Can the user recover from missing setup or a failed operation?
- Are the consequences of paid, outbound, or destructive actions clear?
- Can users operate the main flow with a keyboard?
- Does mobile preserve the information hierarchy and usable controls?

## Report

| Screen or workflow | Grade | Observed evidence | Primary issue |
| --- | --- | --- | --- |
| Task dashboard | C, provisional | Code shows the create action only inside a menu | First action may be hard to discover; verify in the rendered UI |

Use the rubric in [SKILL.md](../SKILL.md). Record whether evidence comes from code, screenshots, an exercised app, or user observation. A UI grade does not replace accessibility checks or user research.
