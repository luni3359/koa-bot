# @client.event
# async def on_message(message):
#     # <crow noises>
#     # say = lambda s: client.send_message(message.channel, s)
#     def say(s): return client.send_message(message.channel, s)

#     if message.author == client.user or str(message.channel) != "koa-bot":
#         return

#     await say("Hi there, " + str(message.author.display_name) + "!")

# @client.event
# async def on_message(message):
#     if message.content.startswith('$greet'):
#         send(1,2,3)
#         msg = await client.wait_for_message(author=message.author, content='hello')
#         await client.send_message(message.channel, 'Hello.')





 # if len(urls) > 0:
    #     await channel.send("Your message contains a link.")

    #     for url in urls:
    #         await channel.send(url)

    # if message.content.startswith(">koa"):
    #     await channel.send("Say hello!")

    #     def check(m):
    #         return m.content == "hello" and m.channel == channel

    #     msg = await client.wait_for("message", check=check)
    #     await channel.send("Hello {.author}!".format(msg))





    # if len(message.embeds) > 0:
    #     await channel.send("embeds present!")






# @client.event
# async def on_message(message):
#     if message.content.startswith('$thumb'):
#         channel = message.channel
#         await channel.send('Send me that 👍 reaction, mate')

#         def check(reaction, user):
#             return user == message.author and str(reaction.emoji) == '👍'

#         try:
#             reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=check)
#         except asyncio.TimeoutError:
#             await channel.send('👎')
#         else:
#             await channel.send('👍')
