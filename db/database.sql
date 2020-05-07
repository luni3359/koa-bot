CREATE DATABASE koabot;

USE koabot;
CREATE TABLE discordUser (
    userId INT,
    userName VARCHAR(255),
    userBirthday DATE,
    -- Should appear as America/New_York
    -- https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
    preciseTimeZone VARCHAR(255),
    -- https://en.wikipedia.org/wiki/List_of_time_zone_abbreviations
    timeZone VARCHAR(10),
    CONSTRAINT pk_discUser PRIMARY KEY (userId)
);

CREATE TABLE discordServer (
    serverId INT,
    serverName VARCHAR(255),
    CONSTRAINT pk_discServer PRIMARY KEY (serverId)
);

CREATE TABLE discordServerUser (
    userId INT,
    serverId INT,
    userNickname VARCHAR(255),
    CONSTRAINT pk_discServUser PRIMARY KEY (userId, serverId),
    CONSTRAINT fk_discUserid_discServUser FOREIGN KEY (userId) REFERENCES discordUser(userId),
    CONSTRAINT fk_discServid_discServUser FOREIGN KEY (serverId) REFERENCES discordServer(serverId)
);

CREATE TABLE discordServerChannel (
    channelId INT,
    serverId INT,
    channelName VARCHAR(255),
    channelTopic VARCHAR(255),
    isNsfw TINYINT(1),
    lastMessageTime DATETIME,
    CONSTRAINT pk_discServChan PRIMARY KEY (channelId, serverId),
    CONSTRAINT fk_discServid_discServChan FOREIGN KEY (serverId) REFERENCES discordServer(serverId)
);

CREATE TABLE artist (
    artistId INT,
    artistNickname VARCHAR(255),
    artistBirthday DATE,
    CONSTRAINT pk_artistid PRIMARY KEY (artistId)
);

CREATE TABLE twitterAccount (
    -- the Twitter id is a signed 52-bit int, but it's preferable to pick id_str field
    userId VARCHAR(20),
    userName VARCHAR(255),
    screenName VARCHAR(125),
    verifiedAcc TINYINT(1),
    userDesc VARCHAR(255),
    -- in UTC
    creationDate DATETIME,
    CONSTRAINT pk_twitterAcc PRIMARY KEY (userId)
);

CREATE TABLE artistTwitter (
    artistId INT,
    twitterId VARCHAR(20),
    CONSTRAINT pk_artistTwit PRIMARY KEY (artistId, twitterId)
    CONSTRAINT fk_artidArtTwit FOREIGN KEY (artistId) REFERENCES artist(artistId)
    CONSTRAINT fk_twitidArtTwit FOREIGN KEY (twitterId) REFERENCES twitterAccount(userId)
);

CREATE TABLE userAvatar (
    avatarId INT,
    userId INT,
    avatarUrl VARCHAR(255),
    CONSTRAINT pk_avatarid PRIMARY KEY (avatarId),
    CONSTRAINT fk_userUserAvat FOREIGN KEY (userId) REFERENCES discordUser(userId)
);
