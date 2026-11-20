---
name: Review Variance
description: Analyze budget vs actual variances with drill-down, interpretation guidance, and corrective action recommendations.
---

# Review Variance

Help me analyze budget variances:

1. Ask which legal entity and budget version (or find the current approved budget)
2. Fetch variance data with the variance reports (`variance_summary`, `variance_by_account`, `variance_by_period`) or the exact `budget_actual` report
3. Show summary: total budget, total actual, total variance, overall variance %
4. Ask which materiality thresholds to use (suggest examples, in the entity's currency), then highlight the top unfavorable variances
5. For each flagged item, classify the variance type (timing, volume, price, mix, one-time)
6. Offer drill-down by period, account, project, employee, or dimension
7. Suggest corrective actions: should we revise the forecast? escalate? reallocate?
8. If requested, help create a forecast revision based on the variance findings

Use the Budget Planning skill for interpretation guidance.
