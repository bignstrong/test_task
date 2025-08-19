-- Create configurations table
CREATE TABLE configurations (
    id SERIAL PRIMARY KEY,
    service TEXT NOT NULL,
    version INTEGER NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(service, version)
);

-- Create index for faster lookups
CREATE INDEX idx_configurations_service ON configurations(service);
CREATE INDEX idx_configurations_service_version ON configurations(service, version);