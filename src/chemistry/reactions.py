"""Contains code for managing the reactions."""

import json
import random
import string

from config import SRC_PATH

already_sent_reactions = []


class Reaction:
    """
    Reaction class to easily manage the reactions. Manipulates with how the reaction is presented.

    :param not_parsed_reaction: It is a list of the reactants and the reaction obtained from reactions.json.
    :param product: It is the product formed by the reactants during the reaction.

    Attributes:
        :reaction: Contains the full chemical reaction of the reactants side.
        :reactants: Contains the reactants present in the chemical reaction.
    """

    def __init__(self, not_parsed_reaction: list[str], product: str):
        self.reaction = not_parsed_reaction[0]
        self.reactants = [*not_parsed_reaction[1:]]
        self.product = product

    def html_reaction(self) -> str:
        """Converts the text formatting to contain subscript in html."""
        html_reaction = self.reaction
        for digit in string.digits:
            html_reaction = html_reaction.replace(digit, f"<sub>{digit}</sub>")
        return html_reaction

    def options(self) -> dict[str, list]:
        """Generate suitable options for the reactants to choose for."""
        pass

    def omit(self, position: int):
        to_omit = self.reactants[position]
        return self.reaction.replace(to_omit, "XX")

    def json(self, omit_number) -> dict[str, str]:
        return {
            "type": "reaction",
            "reaction_original": self.reaction,
            "reaction": self.omit(omit_number),
            "reactants": self.reactants,
            "products": self.product
        }


with open(str(SRC_PATH / "chemistry" / "reactions.json"), "r") as f:
    reactions_cache = json.load(f)


def get_reaction() -> Reaction:
    """Gets a chemical reaction from the reactions.json file."""
    reactions = reactions_cache

    if already_sent_reactions:
        reactions = reactions[:]
        for reaction_type, reaction_list in reactions.items():
            for reaction in reaction_list:
                if reaction in already_sent_reactions:
                    reactions[reaction_type].remove(reaction)

    selected_react_type = random.choice(tuple(reactions.keys()))
    selected_react = random.choice(reactions[selected_react_type])
    already_sent_reactions.append(selected_react)
    return Reaction(selected_react, selected_react_type)


if __name__ == '__main__':
    # with open("reactions.json", "w") as f:
    #     json.dump(writeable, f, indent=2)
    r = get_reaction()
    print(r.reaction, r.reactants, r.html_reaction())
