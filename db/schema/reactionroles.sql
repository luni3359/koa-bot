CREATE TABLE IF NOT EXISTS reactionRoles (
    rrId INTEGER NOT NULL,
    isEnabled INTEGER DEFAULT TRUE,
    dateCreated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_reactRole PRIMARY KEY (rrId)
);

CREATE TABLE IF NOT EXISTS discordServerRR (
    rrId INTEGER NOT NULL,
    serverId INTEGER NOT NULL,
    CONSTRAINT pk_discServRR PRIMARY KEY (rrId, serverId),
    CONSTRAINT fk_discRRid_discServRR FOREIGN KEY (rrId) REFERENCES reactionRoles(rrId),
    CONSTRAINT fk_discServid_discServRR FOREIGN KEY (serverId) REFERENCES discordServer(serverId)
);

CREATE TABLE IF NOT EXISTS discordRole (
    roleId INTEGER NOT NULL,
    roleDId INTEGER NOT NULL UNIQUE,
    CONSTRAINT pk_discRole PRIMARY KEY (roleId)
);

CREATE TABLE IF NOT EXISTS rrRelationships (
    rrId INTEGER NOT NULL,
    roleId INTEGER NOT NULL,
    CONSTRAINT fk_reactRoleid_rrRel FOREIGN KEY (rrId) REFERENCES reactionRoles(rrId),
    CONSTRAINT fk_discRoleid_rrRel FOREIGN KEY (roleId) REFERENCES discordRole(roleId)
);
