-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create Schemas
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS conversation;
CREATE SCHEMA IF NOT EXISTS incident;

-- Table: identity.users
CREATE TABLE IF NOT EXISTS identity.users (
    user_id BIGSERIAL PRIMARY KEY,
    user_name VARCHAR(100) NOT NULL,
    user_role VARCHAR(50) NOT NULL,
    password VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: conversation.messages
CREATE TABLE IF NOT EXISTS conversation.messages (
    message_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_messages_user
        FOREIGN KEY (user_id)
        REFERENCES identity.users(user_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_message_role
        CHECK (role IN ('user', 'assistant'))
);

-- Table: incident.incidents
CREATE TABLE IF NOT EXISTS incident.incidents (
    id BIGSERIAL PRIMARY KEY,
    incident_id VARCHAR(30) NOT NULL UNIQUE,
    short_description TEXT NOT NULL,
    description TEXT,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    assignment_group VARCHAR(150),
    assigned_to VARCHAR(150),
    criticality SMALLINT,
    criticality_description TEXT,
    state VARCHAR(50) NOT NULL,
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    opened_by VARCHAR(150),
    closed_by VARCHAR(150),
    resolution TEXT,
    root_cause_analysis TEXT,
    service VARCHAR(150),
    document_text TEXT,
    embedding VECTOR(768),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_incident_criticality
        CHECK (criticality IS NULL OR criticality BETWEEN 1 AND 4),

    CONSTRAINT chk_incident_state
        CHECK (
            state IN (
                'Open',
                'In Progress',
                'Pending',
                'Closed'
            )
        )
);

-- Indexing for Incidents
CREATE INDEX IF NOT EXISTS idx_incidents_category ON incident.incidents(category);
CREATE INDEX IF NOT EXISTS idx_incidents_subcategory ON incident.incidents(subcategory);
CREATE INDEX IF NOT EXISTS idx_incidents_service ON incident.incidents(service);
CREATE INDEX IF NOT EXISTS idx_incidents_state ON incident.incidents(state);
CREATE INDEX IF NOT EXISTS idx_incidents_criticality ON incident.incidents(criticality);
CREATE INDEX IF NOT EXISTS idx_incidents_assignment_group ON incident.incidents(assignment_group);

-- Indexing for Conversation
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON conversation.messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_created ON conversation.messages(user_id, created_at);

-- Create Roles
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'incident_app') THEN
        CREATE ROLE incident_app LOGIN PASSWORD 'app_password';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'incident_ai') THEN
        CREATE ROLE incident_ai LOGIN PASSWORD 'ai_password';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'incident_ingest') THEN
        CREATE ROLE incident_ingest LOGIN PASSWORD 'ingest_password';
    END IF;
END $$;

-- Grant permissions to roles
GRANT ALL ON SCHEMA identity, conversation, incident TO postgres, incident_app, incident_ai, incident_ingest;
GRANT ALL ON ALL TABLES IN SCHEMA identity, conversation, incident TO postgres, incident_app, incident_ai, incident_ingest;
GRANT ALL ON ALL SEQUENCES IN SCHEMA identity, conversation, incident TO postgres, incident_app, incident_ai, incident_ingest;
