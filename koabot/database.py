import os
import sqlite3

import appdirs

BOT_DIRNAME = 'koa-bot'
CACHE_DIR = appdirs.user_cache_dir(BOT_DIRNAME)


conn = sqlite3.connect(os.path.join(CACHE_DIR, 'dbTest.sqlite3'))
c = conn.cursor()

with open('db/database.sql') as f:
    sql_script = f.read()
c.executescript(sql_script)

c.execute("INSERT INTO discordUser(userDId, userName) VALUES (123123, 'firstuser')")
conn.commit()

# c.execute("SELECT last_insert_rowid()")
# print(c.fetchone()) # returns a tuple...?

userId = c.lastrowid

c.execute("INSERT INTO discordServer(serverDId, serverName) VALUES (43216, 'my server')")
# c.execute("INSERT INTO discordServer(serverId, serverName) VALUES (43216, 'my server', strftime('%s', 'now'))") # unix version
conn.commit()

serverId = c.lastrowid

c.execute("INSERT INTO discordServerUser(userId, serverId) VALUES (?, ?)", [userId, serverId])
conn.commit()

c.execute("SELECT * FROM discordUser")
for row in c.fetchall():
    print(row)

c.execute("SELECT * FROM discordServer")
for row in c.fetchall():
    print(row)

c.execute("SELECT d.userName, s.serverName FROM discordUser AS d, discordServer AS s, discordServerUser AS dsu WHERE dsu.userId=d.userId AND dsu.serverId=s.serverId")
for row in c.fetchall():
    print(row)

c.close()
