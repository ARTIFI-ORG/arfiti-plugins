# Financial Ratios

Ratios are plugin analysis on top of the server reports. Every input is a server figure; the classification behind "current", "cash", "receivables", "payables" and "inventory", and the example bands, live in `scripts/ratio_policy.json`. That file is example policy, edited per firm or client.

| Area | Ratio | Formula | Inputs |
|---|---|---|---|
| Profitability | Gross margin | gross profit ÷ revenue | income statement totals |
| Profitability | Operating margin | operating profit ÷ revenue | income statement totals |
| Profitability | Net margin | net income ÷ revenue | income statement totals |
| Liquidity | Current ratio | current assets ÷ current liabilities | balance sheet subtype groups (policy lists) |
| Liquidity | Quick ratio | (current assets − inventory) ÷ current liabilities | balance sheet subtype groups (policy lists) |
| Leverage | Liabilities to equity | total liabilities ÷ total equity | balance sheet totals |
| Efficiency | DSO | receivables ÷ revenue × days in the period | balance sheet groups, income statement |
| Efficiency | DPO | payables ÷ cost of sales × days in the period | balance sheet groups, income statement |
| Efficiency | Inventory days | inventory ÷ cost of sales × days in the period | balance sheet groups, income statement |

## Rules

- Days in the period is the actual length of the income statement period (a 30-day month is 30), never a fixed 365. The figures use closing balances: an approximation, not an average.
- A ratio is unavailable when an input is null, the report is incomplete or the denominator is zero. Never substitute zero.
- Describe a ratio against "the example band" from the policy file. Don't call it "healthy" or "weak": the right range depends on the industry, the business model and the firm's own policy.
- Compare ratios over time and with each other rather than drawing a conclusion from one value.
