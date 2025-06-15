-- Create apple_stock table
CREATE TABLE IF NOT EXISTS apple_stock (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    open DECIMAL(10, 2) NOT NULL,
    high DECIMAL(10, 2) NOT NULL,
    low DECIMAL(10, 2) NOT NULL,
    close DECIMAL(10, 2) NOT NULL,
    volume BIGINT NOT NULL
);

-- Create sample analytics tables
CREATE TABLE IF NOT EXISTS daily_metrics (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    avg_price DECIMAL(10, 2) NOT NULL,
    volume_change_pct DECIMAL(10, 2),
    price_change_pct DECIMAL(10, 2)
);

CREATE TABLE IF NOT EXISTS monthly_metrics (
    id SERIAL PRIMARY KEY,
    month DATE UNIQUE NOT NULL,
    avg_price DECIMAL(10, 2) NOT NULL,
    max_price DECIMAL(10, 2) NOT NULL,
    min_price DECIMAL(10, 2) NOT NULL,
    total_volume BIGINT NOT NULL,
    volatility DECIMAL(10, 2)
);

-- Copy data from CSV (this will be handled by the application)