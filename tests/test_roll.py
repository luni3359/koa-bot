import random
import re
from heapq import nlargest, nsmallest
from typing import Literal

import pytest
from num2words import num2words

from koabot.patterns import DICE_PATTERN

# from pytest_mock import mocker
# from koabot.cogs.game import Game, RollEmptyThrow, RollInvalidSyntax


# def test_roll():
#     bot = mocker.Mock()
#     game = Game(bot=bot)
#     roll_log = game.dice_roll()
#     print(roll_log)
#     assert roll_log == ""

random.seed(123)


class RollMatch:
    """Roll object helper
    -----------------------
    type::
    sign::
    quantity::
    pips::
    keep::
    raw_points::
    limited_quantity::
    keep_type::'h' | 'l'
        Whether the kept rolled dice should be of the highest or the lowest values.
    keep_type_full::'highest' | 'lowest'
        The full notation of `keep_type`.
    keep_quantity::int
        The amount of dice to keep.
    """

    def __init__(self, dice_match: re.Match) -> None:
        self.type: str = None                       # points, roll
        self.sign: str = dice_match.group(1)        # +, -
        self.quantity: int = dice_match.group(2)    # 0, 1, 20
        self.pips: int = dice_match.group(3)        # 0, 1, 6, 32
        self.keep: str = dice_match.group(4)        # kh3, kl2
        self.raw_points: int = dice_match.group(5)
        self.limited_quantity = False

        if self.keep:
            self._keep_type = self.keep[1]
            self._keep_quantity = int(self.keep[2:])

        if not self.quantity:
            self.quantity = 1
        else:
            self.quantity = int(self.quantity)
            if self.quantity > 100:
                self.limited_quantity = True

            self.quantity = min(self.quantity, 100)

        if not self.pips:
            self.type = "points"
            self.pips = 0
        else:
            self.type = "roll"
            self.pips = int(self.pips)

        if not self.raw_points:
            self.raw_points = 0

        if not self.sign:
            self.sign = '+'

        if self.sign == '+':
            self.raw_points = int(self.raw_points)
        else:
            self.raw_points = -int(self.raw_points)

    @property
    def keep_type(self) -> Literal['h', 'l']:
        return self._keep_type

    @property
    def keep_type_full(self) -> Literal['highest', 'lowest']:
        return 'highest' if self._keep_type == 'h' else 'lowest'

    @property
    def keep_quantity(self) -> int:
        return self._keep_quantity

    @keep_quantity.setter
    def keep_quantity(self, value: int):
        if not isinstance(value, int):
            raise TypeError("`keep_quantity can only receive `int` type.`")
        self._keep_quantity = value


class RollInvalidSyntax(Exception):
    def __init__(self, message="Unable to parse roll string"):
        super(RollInvalidSyntax, self).__init__(message)


class RollEmptyThrow(Exception):
    def __init__(self, message="The roll has no dice or has zero-pip dice"):
        super(RollEmptyThrow, self).__init__(message)


def dice_roll(roll_string: str) -> str:
    matches_found: list[RollMatch] = []
    roll_count = 0
    i = 0
    while i < len(roll_string):
        if roll_string[i] == ' ':
            i += 1
            continue

        pattern_match = DICE_PATTERN.match(roll_string, i)

        if pattern_match:
            match = RollMatch(pattern_match)

            if match.pips and match.quantity > 0:
                roll_count += match.quantity
            elif match.type == "roll":
                roll_count += 1

            matches_found.append(match)
            i = pattern_match.end()
            continue

        raise RollInvalidSyntax()

    # there should always be at least one roll - never do raw math
    if roll_count == 0:
        raise RollEmptyThrow()

    total_sum = 0
    logic_string = ""
    # die_or_dice = roll_count > 1 and 'dice' or 'die'
    # message = f">>> {ctx.author.mention} rolled the {die_or_dice}.\n"
    message = ">>> "

    for i, match in enumerate(matches_found):
        if match.type == "points":
            if match.sign == '+':
                message += "Add "
            else:
                message += "Subtract "

            s_or_no_s = 's' if (abs(match.raw_points) > 1 or match.raw_points == 0) else ''

            message += f"{abs(match.raw_points)} point{s_or_no_s}.\n"
            logic_string += f"{match.sign} __{abs(match.raw_points)}__ "
            total_sum += match.raw_points
            continue

        dice_or_die = 'dice' if match.quantity != 1 else 'die'

        if match.limited_quantity:
            message += '\\*'

        if match.quantity == 0 or match.pips == 0:
            message += f"{num2words(match.quantity).capitalize()} {match.pips}-sided {dice_or_die}. Nothing to roll.  **0.**\n"
            continue

        roll_list: list[int] = []

        if match.keep:
            if match.keep_quantity != 0:
                keep_list: list[int] = []

                if (overkeep := match.keep_quantity > match.quantity):
                    match.keep_quantity = match.quantity
            else:
                match.keep = ''

        if match.sign == '+':
            message += f"{num2words(match.quantity).capitalize()}"
        else:
            message += f"Minus {num2words(match.quantity)}"

        message += f" {match.pips}-sided {dice_or_die} for a "

        for j in range(0, match.quantity):
            die_roll = random.randint(1, match.pips)
            roll_list.append(die_roll)

            if match.keep:
                keep_list.append(die_roll)

                if len(keep_list) >= match.keep_quantity:
                    if match.keep_type == 'l':
                        keep_list = nsmallest(match.keep_quantity, keep_list)
                    elif match.keep_type == 'h':
                        keep_list = nlargest(match.keep_quantity, keep_list)

            # Final die in group throw
            if j == match.quantity - 1:
                if match.quantity == 1:
                    message += f'{die_roll}.'

                    if match.pips != 1 and (die_roll == match.pips or die_roll == 1):
                        message += f" **Nat {die_roll}!**"
                else:
                    message += f'and a {die_roll}.'

                    if match.pips != 1:
                        max_nats = roll_list.count(match.pips)
                        min_nats = roll_list.count(1)

                        if len(roll_list) in [max_nats, min_nats]:
                            message += f" **FULL NAT {die_roll}!**"
                        elif max_nats or min_nats:
                            message += " **"
                            if max_nats:
                                message += f"Nat {match.pips} x{max_nats}! "
                            if min_nats:
                                message += f"Nat 1 x{min_nats}!"
                            message += "**"

                if match.keep:
                    message += f'\nKeep the {match.keep_type_full} '

                    if match.keep_quantity > 1:
                        message += f'{num2words(match.keep_quantity)}' + (overkeep and '*' or '') + ': ' + ', '.join(
                            map(str, keep_list[:match.keep_quantity-1])) + f' and a {keep_list[match.keep_quantity-1]}.'
                    else:
                        message += f'number: {keep_list[0]}.'

                    if i != 0 or match.sign != '+':
                        logic_string += f"{match.sign} "

                    if len(keep_list) > 1 and (len(matches_found) > 1 or match.sign != "+"):
                        logic_string += f"__({' + '.join(map(str, keep_list))})__ "
                    else:
                        logic_string += f"__{' + '.join(map(str, keep_list))}__ "

                    if match.sign == '+':
                        total_sum += sum(keep_list)
                    else:
                        total_sum -= sum(keep_list)

                message += '\n'
            elif j == match.quantity - 2:
                message += f'{die_roll} '
            else:
                message += f'{die_roll}, '

            if not match.keep:
                if match.sign == '+':
                    total_sum += die_roll
                else:
                    total_sum -= die_roll

        if not match.keep:
            if i != 0 or match.sign != '+':
                logic_string += f"{match.sign} "

            if len(roll_list) > 1 and (len(matches_found) > 1 or match.sign != "+"):
                logic_string += f"__({' + '.join(map(str, roll_list))})__ "
            else:
                logic_string += f"__{' + '.join(map(str, roll_list))}__ "

    if logic_string:
        message += f"{logic_string}\n"

    message += f"For a total of **{total_sum}.**"

    return message[0:2000]


def test_one_roll():
    roll_log = dice_roll("d6")
    print(roll_log)
    assert roll_log == ">>> One 6-sided die for a 1. **Nat 1!**\n__1__ \nFor a total of **1.**"


pip_data = [
    ("d0", ">>> One 0-sided die. Nothing to roll.  **0.**\nFor a total of **0.**"),
    ("d1", ">>> One 1-sided die for a 1.\n__1__ \nFor a total of **1.**"),
    ("d6", ">>> One 6-sided die for a 1. **Nat 1!**\n__1__ \nFor a total of **1.**"),
    ("d9999", ">>> One 9999-sided die for a 858.\n__858__ \nFor a total of **858.**"),
]


@pytest.mark.parametrize("input,expected", pip_data)
def test_pips(input: str, expected: str):
    random.seed(123)
    roll_log = dice_roll(input)
    print(roll_log)
    assert roll_log == expected


exception_data = [
    ("abcde", RollInvalidSyntax),
    ("one d6", RollInvalidSyntax),
    ("6 + 3", RollEmptyThrow),
    ("0", RollEmptyThrow),
]


@pytest.mark.parametrize("input,expected_exception", exception_data)
def test_exceptions(input: str, expected_exception: Exception):
    random.seed(123)
    with pytest.raises(expected_exception):
        roll_log = dice_roll(input)
        print(roll_log)
