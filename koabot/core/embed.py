import discord
from typing_extensions import Self


class Embed(discord.Embed):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def __add__(self, other: Self) -> Self:
        embed = Embed()

        # Way shorter but risky :(
        # for property in ['author', 'footer', 'color']:
        #     if eval(f"self.{property}"):
        #         eval(f"embed.{property} = self.{property}")
        #     elif eval(f"other.{property}"):
        #         eval(f"embed.{property} = other.{property}")

        description = None
        if self.description:
            description = self.description
        elif other.description:
            description = other.description

        embed.description = description

        author = None
        if self.author:
            author = self.author
        elif other.author:
            author = other.author

        if author:
            embed.set_author(name=author.name, url=author.url, icon_url=author.icon_url)

        image = None
        if self.image:
            image = self.image
        elif other.image:
            image = other.image

        if image:
            embed.set_image(url=image.url)

        footer = None
        if self.footer:
            footer = self.footer
        elif other.footer:
            footer = other.footer

        if footer:
            embed.set_footer(text=footer.text, icon_url=footer.icon_url)

        if self.color:
            embed.color = self.color
        elif other.color:
            embed.color = other.color

        fields = None
        if self.fields:
            fields = self.fields
        elif other.fields:
            fields = other.fields

        if fields:
            for i, field in enumerate(fields):
                embed.insert_field_at(i, name=field.name, value=field.value, inline=field.inline)

        if self.timestamp:
            embed.timestamp = self.timestamp
        else:
            embed.timestamp = other.timestamp

        return embed

    __radd__ = __add__


class EmbedGroup(Embed):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self._embeds: list[Embed] = []
        self._embed_queue: list[Embed] = []
        self._embeds_lock: bool = False
        self._first: discord.Embed = Embed()
        self._last: discord.Embed = Embed()
        self._merge_first_and_last: bool = True
        self._max_group_length: int = 5

    @property
    def embeds(self) -> list[discord.Embed]:
        """VS Code reading this causes this property to execute multiple times in a row"""
        if self._embeds:
            return self._embeds

        # Lock to prevent debugging sessions from running this too many times
        if self._embeds_lock:
            return []

        self._embeds_lock = True

        if self.merge_first_and_last:
            if len(self._embed_queue) > 1:
                first_embed = self._embed_queue[0]
                last_embed = self._embed_queue[-1]

                if self.first != Embed():
                    self._embed_queue[0] = first_embed + self.first

                if self.last != Embed():
                    self._embed_queue[-1] = last_embed + self.last

                for embed in self._embed_queue:
                    self._embeds.append(embed + self)
            elif len(self._embed_queue) == 1:
                embed = self._embed_queue[0]

                if self.first != Embed():
                    embed = embed + self.first

                if self.last != Embed():
                    embed = embed + self.last

                self._embeds.append(embed + self)
        else:
            if self.first != Embed():
                self._embeds.append(self.first + self)

            if self.last != Embed():
                self._embeds.append(self.last + self)

        self._embeds_lock = False

        return self._embeds

    @property
    def first(self) -> discord.Embed:
        """The properties that the first embed in the embed group will have"""
        return self._first

    @property
    def last(self) -> discord.Embed:
        """The properties that the last embed in the embed group will have"""
        return self._last

    @property
    def merge_first_and_last(self) -> None:
        return self._merge_first_and_last

    @merge_first_and_last.setter
    def merge_first_and_last(self, value: bool) -> None:
        self._merge_first_and_last = value

    @property
    def max_group_length(self) -> int:
        return self._max_group_length

    @max_group_length.setter
    def max_group_length(self, value: int) -> None:
        if not isinstance(value, int):
            raise ValueError("`max_group_length` must be of type `int`.")

        if value < 1:
            raise ValueError("`max_group_length` must be an integer 1 and over")

        self._max_group_length = value

    def add(self) -> discord.Embed:
        embed = Embed()
        self._embed_queue.append(embed)
        return embed
