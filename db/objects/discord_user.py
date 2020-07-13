class DiscordUser:
    def __init__(self, user_id, user_did, user_name):
        self.user_id = user_id
        self.user_did = user_did
        self.user_name = user_name

    @property
    def fully_qualified_name(self):
        return self.user_name + '#1234'
