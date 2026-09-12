\# Nifty100 Financial Intelligence



A financial analytics and intelligence platform for analyzing Nifty 100 companies using financial ratios, valuation metrics, peer comparisons, screening, trends, sector analysis, and capital-allocation insights.



\## Project Overview



\*\*Nifty100 Financial Intelligence\*\* transforms financial datasets into actionable insights through an interactive Streamlit dashboard.



The project provides:



\* Company financial analysis

\* Financial ratio analysis

\* Multi-factor stock screening

\* Peer percentile comparison

\* Composite quality scoring

\* Valuation analysis

\* Sector-level analysis

\* Historical financial trends

\* Capital allocation analysis

\* Annual report information

\* Excel-based analytical reports



\---



\## Technology Stack



\* \*\*Python 3.11\*\*

\* \*\*SQLite\*\*

\* \*\*Pandas\*\*

\* \*\*NumPy\*\*

\* \*\*Streamlit\*\*

\* \*\*Plotly\*\*

\* \*\*Matplotlib\*\*

\* \*\*OpenPyXL\*\*

\* \*\*Pytest\*\*

\* \*\*Git \& GitHub\*\*



\---



\## Project Structure



```text

N100-Financial-Intelligence/

│

├── data/

│   └── Financial datasets

│

├── output/

│   ├── valuation\_summary.xlsx

│   ├── valuation\_flags.csv

│   └── Other analytical reports

│

├── reports/

│   └── radar\_charts/

│

├── src/

│   ├── analytics/

│   │   ├── composite\_score.py

│   │   ├── export\_screener.py

│   │   └── valuation.py

│   │

│   ├── dashboard/

│   │   ├── app.py

│   │   ├── utils/

│   │   └── pages/

│   │       ├── 01\_home.py

│   │       ├── 02\_profile.py

│   │       ├── 03\_screener.py

│   │       ├── 04\_peers.py

│   │       ├── 05\_trends.py

│   │       ├── 06\_sectors.py

│   │       ├── 07\_capital.py

│   │       └── 08\_reports.py

│   │

│   └── screener/

│

├── tests/

│

├── nifty100.db

├── README.md

└── requirements.txt

```



\---



\# Dashboard



The project includes an \*\*8-screen Streamlit dashboard\*\* for interactive financial analysis.



\## Running the Dashboard



Open PowerShell in the project root:



```powershell

cd D:\\N100-Financial-Intelligence

```



Activate the virtual environment:



```powershell

.\\.venv\\Scripts\\Activate.ps1

```



Run the dashboard:



```powershell

streamlit run src/dashboard/app.py

```



The dashboard will open in the browser.



\---



\# Dashboard Screens



\## 1. Home



Provides an overview of the Nifty100 Financial Intelligence platform.



Key features:



\* Company universe overview

\* Financial statistics

\* Quick navigation

\* High-level market insights



\---



\## 2. Company Profile



Provides detailed analysis for an individual company.



Displays:



\* Company information

\* Sector

\* Key financial metrics

\* ROE

\* ROCE

\* Net Profit Margin

\* Debt-to-Equity

\* Revenue CAGR

\* Free Cash Flow

\* Historical financial information



Missing values are displayed as \*\*N/A\*\* rather than causing application failures.



\---



\## 3. Screener



Allows users to filter companies using financial criteria.



Available screening factors include:



\* ROE

\* Debt-to-Equity

\* Free Cash Flow

\* Revenue CAGR

\* PAT CAGR

\* Operating Profit Margin

\* P/E

\* P/B

\* Dividend Yield

\* Interest Coverage

\* Market Capitalization

\* Net Profit

\* EPS CAGR

\* Asset Turnover

\* Sales



Preset screeners include:



\* Quality

\* Value

\* Growth

\* Dividend

\* Debt-Free

\* Turnaround



\---



\## 4. Peer Comparison



Compares companies against their respective peer groups.



Features include:



\* Peer groups

\* Benchmark companies

\* Percentile rankings

\* Financial metric comparisons

\* Peer performance analysis

\* Radar charts



Peer groups include areas such as:



\* IT Services

\* Private Banks

\* Public Sector Banks

\* Pharmaceuticals

\* Automobiles

\* FMCG

\* Oil \& Gas

\* Power \& Utilities

\* Steel

\* Life Insurance

\* Consumer Finance



\---



\## 5. Trends



Provides historical financial trend analysis.



Users can:



\* Select a company

\* Select financial metrics

\* View historical trends

\* Analyze year-over-year changes

\* Compare multiple metrics



The page gracefully handles companies with unavailable financial history by displaying a clear data-availability message.



\---



\## 6. Sector Analysis



Provides sector-level financial analysis.



Features include:



\* Sector selection

\* Company comparison

\* ROE analysis

\* Market capitalization analysis

\* Revenue growth

\* Sector KPI statistics

\* Visual comparisons



The sector information is derived from the project sector mapping dataset.



\---



\## 7. Capital Allocation



Analyzes how companies allocate and manage capital.



Companies are categorized into patterns such as:



\* Growth

\* Dividend

\* Debt Reduction

\* Capex Heavy

\* Cash Rich

\* Balanced

\* Mixed



The page provides visual summaries and company-level classification.



\---



\## 8. Annual Reports



Provides annual-report information available in the project dataset.



Users can:



\* Select a company

\* View available report records

\* Access available report links

\* Handle companies where report data is unavailable



Missing report data is handled gracefully without crashing the dashboard.



\---



\# Analytics Modules



\## Financial Ratios



The platform analyzes important financial indicators including:



\* Net Profit Margin

\* Operating Profit Margin

\* Return on Equity

\* Debt-to-Equity

\* Interest Coverage

\* Asset Turnover

\* Free Cash Flow

\* EPS

\* Dividend Payout

\* Revenue CAGR

\* PAT CAGR

\* EPS CAGR



\---



\## Composite Quality Score



Companies are evaluated using multiple financial indicators to create a composite quality score.



The score supports:



\* Company ranking

\* Quality screening

\* Peer comparison

\* Investment-oriented analysis



\---



\## Valuation Analysis



The valuation module evaluates companies using:



\* Free Cash Flow Yield

\* P/E Ratio

\* Sector Median P/E

\* Relative valuation



Companies are classified into:



\* \*\*Discount\*\*

\* \*\*Fair\*\*

\* \*\*Caution\*\*

\* \*\*N/A\*\*



The valuation analysis covers the 92-company analytical universe mapped to sectors.



Generated files include:



```text

output/valuation\_summary.xlsx

output/valuation\_flags.csv

```



\---



\# Testing



The project uses Pytest for validation.



Run all tests:



```powershell

pytest -q

```



The project successfully completed the major analytics and dashboard validation stages.



\---



\# Integration QA



During Day 27, the dashboard was tested across multiple sectors and companies.



Tested sectors:



\* IT

\* Financials

\* FMCG

\* Energy

\* Healthcare



The QA process covered:



\* All 8 dashboard screens

\* Multiple company tickers

\* Partial-data companies

\* Missing financial metrics

\* Extreme screener values

\* Chart sizing

\* Page stability

\* Company Profile performance



\### Partial Data



Companies with unavailable financial data do not crash the application.



Example:



```text

No financial trend data available for AGTL.

```



\### Missing Metrics



Unavailable metrics are displayed as:



```text

N/A

```



instead of causing errors.



\### Performance



Company Profile load-time testing:



| Ticker    | Load Time |

| --------- | --------: |

| TCS       |   1.2 sec |

| INFY      |   1.1 sec |

| HDFCBANK  |   1.4 sec |

| RELIANCE  |   1.3 sec |

| SUNPHARMA |   1.2 sec |



\*\*Average:\*\* 1.24 seconds



\*\*Requirement:\*\* Under 3 seconds



\*\*Result:\*\* PASS



\---



\# Sprint 4 Retrospective



\## UX Decisions



\* Dashboard navigation was divided into eight focused screens.

\* Financial metrics were presented using clear KPI cards.

\* Charts were used where visual trends improved understanding.

\* Company and sector selection was implemented using simple interactive controls.

\* Missing information was displayed using clear N/A or data-unavailable messages.

\* Dashboard pages were designed to avoid unnecessary complexity for end users.



\## Data Edge Cases



During development and QA, several data-quality cases were identified:



\* Companies with missing financial records

\* Companies with fewer historical records

\* Missing FCF values

\* Missing annual report information

\* Missing sector information in the primary company table

\* Different data types for year fields

\* Partial datasets for individual companies



These cases were handled through validation, joins with the appropriate source tables, and graceful dashboard messaging.



\## Performance Findings



Company Profile performance was tested using five companies.



All five loaded in less than 3 seconds.



Average load time:



\*\*1.24 seconds\*\*



The dashboard therefore met the defined performance requirement.



\---



\# Sprint 4 Completion



Sprint 4 delivered:



\* Complete 8-screen Streamlit dashboard

\* Company profile analysis

\* Advanced screener

\* Peer comparison

\* Trend analysis

\* Sector analysis

\* Capital allocation analysis

\* Annual report screen

\* Valuation module

\* Valuation reports

\* Integration QA

\* Missing-data handling

\* Performance validation

\* Dashboard documentation



\*\*Sprint 4 Status: COMPLETE\*\*



\---



\# How to Use



1\. Clone or open the project.

2\. Create/activate the Python virtual environment.

3\. Install dependencies.

4\. Ensure the SQLite database is available.

5\. Start Streamlit.



```powershell

.\\.venv\\Scripts\\Activate.ps1

streamlit run src/dashboard/app.py

```



6\. Open the dashboard in the browser.

7\. Select a company or analytical screen.

8\. Explore financial metrics, rankings, trends, sectors, valuation, and reports.



\---



\# Project Outcome



The Nifty100 Financial Intelligence platform provides a centralized interface for analyzing financial performance and comparing companies using structured financial data.



It combines:



\*\*Data → Financial Ratios → Screening → Peer Analysis → Valuation → Visualization → Insights\*\*



The final dashboard provides an interactive foundation for financial research and company-level analysis.



