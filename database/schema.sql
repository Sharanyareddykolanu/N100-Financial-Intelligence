PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    ticker TEXT UNIQUE,
    sector TEXT
);

CREATE TABLE IF NOT EXISTS company_sector (
    company_id TEXT PRIMARY KEY,
    sector TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS company_price_history (
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    close_price REAL,
    high_price REAL,
    low_price REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS company_profit_loss (
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    sales REAL,
    operating_profit REAL,
    net_profit REAL,
    eps REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS company_balance_sheet (
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    total_assets REAL,
    total_liabilities REAL,
    total_equity REAL,
    cash REAL,
    debt REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS company_cashflow (
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    operating_cash_flow REAL,
    investing_cash_flow REAL,
    financing_cash_flow REAL,
    free_cash_flow REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS company_ratios (
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    opm REAL,
    tax_rate REAL,
    net_cash REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS company_shareholding (
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    promoter_holding REAL,
    public_holding REAL,
    institutional_holding REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS company_valuation (
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    market_cap REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    dividend_yield REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS company_financials (
    company_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    revenue REAL,
    profit REAL,
    eps REAL,
    dividend REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);