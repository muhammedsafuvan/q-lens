
-- migrate:up

-- QLens user accounts
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(320) NOT NULL,
    name VARCHAR(120) NOT NULL,
    avatar_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Case-insensitive email uniqueness
CREATE UNIQUE INDEX ix_users_email_lower
    ON users (LOWER(email));


-- External authentication identities (Google, Microsoft, Apple, etc.)
CREATE TABLE user_identities (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(40) NOT NULL,
    provider_subject VARCHAR(255) NOT NULL,
    email VARCHAR(320),
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_user_identities_provider_subject
        UNIQUE (provider, provider_subject)
);

CREATE INDEX ix_user_identities_user_id
    ON user_identities (user_id);


-- Workspace membership and authorization roles
CREATE TABLE workspace_members (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_workspace_members_role
        CHECK (role IN ('owner', 'admin', 'member')),

    CONSTRAINT uq_workspace_members_workspace_user
        UNIQUE (workspace_id, user_id)
);

CREATE INDEX ix_workspace_members_user_id
    ON workspace_members (user_id);


-- Hashed refresh tokens with rotation and revocation support
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    family_id UUID NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    replaced_by_token_id UUID REFERENCES refresh_tokens(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_refresh_tokens_user_id
    ON refresh_tokens (user_id);

CREATE INDEX ix_refresh_tokens_family_id
    ON refresh_tokens (family_id);

CREATE INDEX ix_refresh_tokens_expires_at
    ON refresh_tokens (expires_at);


-- Track which dashboard user created an API key.
-- Existing SDK API keys remain valid and have NULL creator initially.
ALTER TABLE api_keys
    ADD COLUMN created_by_user_id UUID
    REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX ix_api_keys_created_by_user_id
    ON api_keys (created_by_user_id);


-- migrate:down

DROP INDEX IF EXISTS ix_api_keys_created_by_user_id;
ALTER TABLE api_keys DROP COLUMN IF EXISTS created_by_user_id;

DROP TABLE IF EXISTS refresh_tokens;
DROP TABLE IF EXISTS workspace_members;
DROP TABLE IF EXISTS user_identities;
DROP TABLE IF EXISTS users;
