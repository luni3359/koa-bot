CREATE TABLE IF NOT EXISTS reactionRoles (
    rrId INTEGER NOT NULL,
    dateCreated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_reactRole PRIMARY KEY (rrId)
);

CREATE TABLE IF NOT EXISTS strEmoji (
    emojiId INTEGER NOT NULL,
    emojiStr TEXT NOT NULL,
    CONSTRAINT pk_strEmoji PRIMARY KEY (emojiId)
);

CREATE TABLE IF NOT EXISTS discordEmoji (
    emojiId INTEGER NOT NULL,
    emojiDId INTEGER NOT NULL UNIQUE,
    dateCreated TEXT,
    CONSTRAINT pk_discEmoji PRIMARY KEY (emojiId)
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
