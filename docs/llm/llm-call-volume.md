# LLM Call Volume Per Analysis Run

## Execution Flow

1. `_parse_filing_sections` splits the raw filing into headings (`src/infrastructure/providers/llm/base.py#L614`). Only headings that match `SECTION_SCHEMAS` (`src/infrastructure/providers/llm/base.py#L794`) move forward.
2. Each matched schema is decomposed into `SubsectionDefinition` entries via `extract_subsection_definitions` (`src/infrastructure/providers/llm/base.py#L875`). Every subsection spawns its own `_analyze_subsection` call and runs concurrently inside `run_concurrent_subsection_analysis` (`src/infrastructure/providers/llm/base.py#L1004`).
3. After the subsection fan-out, the provider issues a section-level summary call (`src/infrastructure/providers/llm/openai.py#L226`).
4. When all sections finish, `analyze_filing_sections` performs one overall filing synthesis (`src/infrastructure/providers/llm/openai.py#L349`).

## Calls Per Section

| Section label | Schema fields that trigger LLM calls | Subsections | Calls per section* |
| --- | --- | --- | --- |
| Item 1 – Business | `operational_overview`, `key_products`, `competitive_advantages`, `strategic_initiatives`, `business_segments`, `geographic_segments`, `supply_chain`, `partnerships` (`src/infrastructure/providers/llm/schemas/business.py#L164`) | 8 | 9 |
| Risk Factors (10-K Item 1A / 10-Q Part II Item 1A) | `risk_factors`, `industry_risks`, `regulatory_risks`, `financial_risks`, `operational_risks`, `esg_risks` (`src/infrastructure/providers/llm/schemas/risk_factors.py#L103`) | 6 | 7 |
| MD&A (10-K Item 7 / 10-Q Part I Item 2) | `key_financial_metrics`, `revenue_analysis`, `profitability_analysis`, `liquidity_analysis`, `operational_highlights`, `market_conditions`, `forward_looking_statements`, `critical_accounting_policies` (`src/infrastructure/providers/llm/schemas/mda.py#L111`) | 8 | 9 |
| Balance Sheet | `asset_composition`, `liability_structure`, `equity_analysis`, `key_ratios` (`src/infrastructure/providers/llm/schemas/balance_sheet.py#L73`) | 4 | 5 |
| Income Statement | `revenue_segments`, `expense_categories`, `profitability_metrics` (`src/infrastructure/providers/llm/schemas/income_statement.py#L66`) | 3 | 4 |
| Cash Flow Statement | `operating_cash_flow`, `investing_cash_flow`, `financing_cash_flow`, `cash_flow_ratios` (`src/infrastructure/providers/llm/schemas/cash_flow.py#L73`) | 4 | 5 |

`*calls per section = subsections + 1 summary call`

Sections without schema coverage still cost one summary call because the provider skips directly to the fallback summary code path.

## Run-Level Totals

Total calls for a run = `Σ(section subsection-count + 1)` for every section detected + `1` final overall call. A typical 10-K that surfaces Business, Risk Factors, MD&A, Balance Sheet, Income Statement, and Cash Flow consumes `(8+1) + (6+1) + (8+1) + (4+1) + (3+1) + (4+1) + 1 overall = 40` OpenAI requests.
