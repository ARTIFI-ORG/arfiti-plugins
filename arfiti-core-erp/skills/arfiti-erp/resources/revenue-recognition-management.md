# Revenue Recognition Management

> Current execution contract: `revenue_schedule.*` aliases use the unified
> amortization executor. Only `straight_line` calculation is supported. Follow
> customer-contracts-management.md for source identity, capacity, daily proration
> and live run reads. Milestone/usage policies need their own approved posting flow.


> **This guide has been merged into [Customer Contracts & Deferred Revenue Recognition](customer-contracts-management.md).**
>
> The unified amortization engine (`amortization_schedule.*` workflows) handles both revenue recognition and prepaid expense amortization. The merged guide covers everything in this file plus the new unified API, financial dimensions, amortization runs, and error recovery.
>
> **Use [customer-contracts-management.md](customer-contracts-management.md) for all revenue recognition tasks.**

---

## Quick Reference (legacy API still works)

The `revenue_schedule.*` workflow calls are backward-compatible aliases that route to the same `amortization_schedule.*` executors:

| Legacy call | Routes to |
|-------------|-----------|
| `submit("revenue_schedule", "create", {...})` | `amortization_schedule.create` with `kind: "revenue"` |
| `submit("revenue_schedule", "recognize", {...})` | `amortization_schedule.recognize` |
| `submit("revenue_schedule", "update", {...})` | `amortization_schedule.update` |
| `submit("revenue_schedule", "cancel", {...})` | `amortization_schedule.cancel` |

Both old and new API calls go through the same Pydantic validators, workflow definitions, and executors. The only difference is the object_type string.

---

**Last Updated:** April 2026

**Superseded by:** [Customer Contracts & Deferred Revenue Recognition](customer-contracts-management.md)
