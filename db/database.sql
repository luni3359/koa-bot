CREATE TABLE IF NOT EXISTS discordUser (
    userId INTEGER NOT NULL,
    userDId INTEGER NOT NULL UNIQUE,
    userName TEXT NOT NULL,
    dateFirstSeen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dateFirstUsed TEXT,
    userBirthday TEXT,
    -- https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
    timeZoneLabel TEXT,
    -- Should appear as America/New_York
    -- https://en.wikipedia.org/wiki/List_of_time_zone_abbreviations
    utcOffset TEXT,
    -- Format UTC±N
    CONSTRAINT pk_discUser PRIMARY KEY (userId)
);

CREATE TABLE IF NOT EXISTS discordServer (
    serverId INTEGER NOT NULL,
    serverDId INTEGER NOT NULL UNIQUE,
    serverName TEXT,
    dateFirstSeen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_discServer PRIMARY KEY (serverId)
);

CREATE TABLE IF NOT EXISTS discordChannel (
    channelId INTEGER NOT NULL,
    channelDId INTEGER NOT NULL UNIQUE,
    serverId INTEGER NOT NULL,
    channelName TEXT,
    channelTopic TEXT,
    isNsfw INTEGER,
    lastMessageTime TEXT,
    CONSTRAINT pk_discChan PRIMARY KEY (channelId)
);

CREATE TABLE IF NOT EXISTS discordServerUser (
    userId INTEGER NOT NULL,
    serverId INTEGER NOT NULL,
    userNickname TEXT,
    CONSTRAINT pk_discServUser PRIMARY KEY (userId, serverId),
    CONSTRAINT fk_discUserid_discServUser FOREIGN KEY (userId) REFERENCES discordUser(userId),
    CONSTRAINT fk_discServid_discServUser FOREIGN KEY (serverId) REFERENCES discordServer(serverId)
);

CREATE TABLE IF NOT EXISTS discordEmoji (
    emojiId INTEGER NOT NULL,
    emojiDId INTEGER NOT NULL UNIQUE,
    dateCreated TEXT,
    CONSTRAINT pk_discEmoji PRIMARY KEY (emojiId)
);

CREATE TABLE IF NOT EXISTS userAvatar (
    avatarId INTEGER NOT NULL,
    userId INTEGER NOT NULL,
    avatarUrl TEXT NOT NULL,
    CONSTRAINT pk_avatarid PRIMARY KEY (avatarId),
    CONSTRAINT fk_userUserAvat FOREIGN KEY (userId) REFERENCES discordUser(userId)
);

-- Glaring issue: wouldn't this too many entries?
-- CREATE TABLE IF NOT EXISTS serverEmojiUsage (
--     emusId integer NOT NULL,
--     serverId INTEGER NOT NULL,
--     emojiId integer NOT NULL,
--     userId integer NOT NULL,
--     dateUsed text NOT NULL DEFAULT CURRENT_TIMESTAMP
-- );
-- CREATE TABLE IF NOT EXISTS botPreview (botPreviewId INTEGER NOT NULL,);
-- CREATE TABLE IF NOT EXISTS botEmbed ();
-- CREATE TABLE IF NOT EXISTS artist (
--     artistId INTEGER NOT NULL,
--     artistNickname TEXT,
--     artistBirthday TEXT,
--     CONSTRAINT pk_artistid PRIMARY KEY (artistId)
-- );
-- CREATE TABLE IF NOT EXISTS twitterAccount (
--     twitterId INTEGER NOT NULL,
--     twitterUserId TEXT NOT NULL UNIQUE, -- the Twitter id is a signed 52-bit int, but it's preferable to pick id_str field
--     userName TEXT,
--     screenName TEXT,
--     userDesc TEXT,
--     verifiedAcc INTEGER DEFAULT 0, -- bool
--     creationDate TEXT,
--     CONSTRAINT pk_twitterAcc PRIMARY KEY (twitterId)
-- );
-- CREATE TABLE IF NOT EXISTS artistTwitter (
--     artistId INTEGER NOT NULL,
--     twitterId INTEGER NOT NULL,
--     CONSTRAINT pk_artistTwit PRIMARY KEY (artistId, twitterId)
--     CONSTRAINT fk_artidArtTwit FOREIGN KEY (artistId) REFERENCES artist(artistId)
--     CONSTRAINT fk_twitidArtTwit FOREIGN KEY (twitterId) REFERENCES twitterAccount(twitterId)
-- );
