-- Day 07 : Exploratory SQL Queries
-- Sprint 1 : N100 Financial Intelligence

-- Q1. Total number of companies
SELECT COUNT(*) AS total_companies
FROM companies;

-- Q2. Number of companies in each sector
SELECT sector, COUNT(*) AS company_count
FROM company_sector
GROUP BY sector
ORDER BY company_count DESC;

-- Q3. List all companies with ticker and sector
SELECT company_id, company_name, ticker, sector
FROM companies
ORDER BY company_name;

-- Q4. Top 10 companies by sales
SELECT c.company_name,
       p.year,
       p.sales
FROM company_profit_loss p
JOIN companies c
ON p.company_id = c.company_id
ORDER BY p.sales DESC
LIMIT 10;

-- Q5. Top 10 companies by net profit
SELECT c.company_name,
       p.year,
       p.net_profit
FROM company_profit_loss p
JOIN companies c
ON p.company_id = c.company_id
ORDER BY p.net_profit DESC
LIMIT 10;

-- Q6. Companies with highest market capitalization
SELECT c.company_name,
       v.year,
       v.market_cap
FROM company_valuation v
JOIN companies c
ON v.company_id = c.company_id
ORDER BY v.market_cap DESC
LIMIT 10;

-- Q7. Average closing price of each company
SELECT c.company_name,
       ROUND(AVG(ph.close_price),2) AS average_close_price
FROM company_price_history ph
JOIN companies c
ON ph.company_id = c.company_id
GROUP BY c.company_name
ORDER BY average_close_price DESC;

-- Q8. Companies with highest operating cash flow
SELECT c.company_name,
       cf.year,
       cf.operating_cash_flow
FROM company_cashflow cf
JOIN companies c
ON cf.company_id = c.company_id
ORDER BY cf.operating_cash_flow DESC
LIMIT 10;

-- Q9. Companies with highest OPM (Operating Profit Margin)
SELECT c.company_name,
       r.year,
       r.opm
FROM company_ratios r
JOIN companies c
ON r.company_id = c.company_id
ORDER BY r.opm DESC
LIMIT 10;

-- Q10. Financial records available for each company
SELECT c.company_name,
       COUNT(f.year) AS financial_years
FROM company_financials f
JOIN companies c
ON f.company_id = c.company_id
GROUP BY c.company_name
ORDER BY financial_years DESC;