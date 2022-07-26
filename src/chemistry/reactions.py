"""Contains code for managing the reactions."""

import json
import random
import string
from typing import Dict, List

# writeable = {"salt": [["HCl + NaOH", "H", "Cl", "Na", "OH"], ["H2SO4 + KOH", "H2", "SO4", "K", "OH"]],
#              "ore extraction": [["FeO + CO", "Fe", "O", "C", "O"], ["H2S + SO2", "H2", "S", "S", "O2"]]}


class Reaction:
    """
    Reaction class to easily manage the reactions. Manipulates with how the reaction is presented.

    :param not_parsed_reaction: It is a list of the reactants and the reaction obtained from reactions.json.
    :param product: It is the product formed by the reactants during the reaction.

    Attributes:
        :reaction: Contains the full chemical reaction of the reactants side.
        :reactants: Contains the reactants present in the chemical reaction.
    """

    def __init__(self, not_parsed_reaction: List[str], product: str):
        self.reaction = not_parsed_reaction[0]
        self.reactants = [*not_parsed_reaction[1:]]
        self.product = product

    def html_reaction(self) -> str:
        """Converts the text formatting to contain subscript in html."""
        html_reaction = self.reaction
        for digit in string.digits:
            html_reaction = html_reaction.replace(digit, f"<sub>{digit}</sub>")
        return html_reaction

    def options(self) -> Dict[str, List]:
        """Generate suitable options for the reactants to choose for."""
        pass


def get_reaction(exclude: List[List[str]] = None) -> Reaction:
    """
    Gets a chemical reaction from the reactions.json file.

    :param exclude: Chemical reactions to exclude.
    """
    with open("reactions.json", "r") as f:
        reactions = json.load(f)

    if exclude:
        for reaction_type, reaction_list in reactions.items():
            for reaction in reaction_list:
                if reaction in exclude:
                    reactions[reaction_type].remove(reaction)

    selected_react_type = random.choice(tuple(reactions.keys()))
    selected_react = random.choice(reactions[selected_react_type])
    return Reaction(selected_react, selected_react_type)


if __name__ == '__main__':
    # with open("reactions.json", "w") as f:
    #     json.dump(writeable, f, indent=2)
    r = get_reaction()
    print(r.reaction, r.reactants, r.html_reaction())
