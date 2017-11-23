import json
import re
import random


class Matchmaker:
    participants = []

    def __init__(self, backup_file, results_file):
        try:
            with open(backup_file, "r") as f:
                self.participants = json.load(f)
        except FileNotFoundError:
            with open(backup_file, "w") as f:
                f.write('[]')
        self.results_file = results_file
        self.backup_file = backup_file

    def add_participant(self, from_field, request):
        new_participant = {
            "request": re.sub('[\n\r]', ' ', request)
        }
        if '<' in from_field:
            split = from_field.split('<')
            new_participant["name"] = split[0]
            new_participant["email"] = split[1].split('>')[0]
        else:
            new_participant["name"] = from_field
            new_participant["email"] = from_field

        for participant in self.participants:
            if participant["email"] == new_participant["email"]:
                participant["request"] = new_participant["request"]
                print("Updating duplicate email from %s" % new_participant["email"])
                return ("Since we have already got an email from you, we updated your request/",
                        new_participant)

        self.participants.append(new_participant)
        print("Adding new participant:")
        print(new_participant)
        with open(self.backup_file, "w") as f:
            json.dump(self.participants, f)

        return ("We've added your request for '" + new_participant["request"] + "' to the list.",
                new_participant)

    def make_matches(self):
        matches = []
        participant_list_clone = list(self.participants)

        #Drunken salesman algorithm
        first_participant = participant_list_clone.pop()
        current_participant = first_participant

        while len(participant_list_clone):
            next_participant = participant_list_clone[random.randint(0, len(participant_list_clone) - 1)]
            participant_list_clone.remove(next_participant)
            matches.append((current_participant, next_participant))
            current_participant = next_participant
        matches.append((current_participant, first_participant))

        """
        for participant in self.participants:
            pot_match = participant_matches[random.randint(0, len(participant_matches) - 1)]
            while pot_match["number"] == participant["number"]:
                if len(participant_matches) == 1:
                    for i, (p, m) in enumerate(matches):
                        if p["number"] != participant["number"] and m["number"] != participant["number"]:
                            del matches[i]
                            matches.append((p, pot_match))
                            matches.append((participant, m))
                            break
                    return []
                pot_match = participant_matches[random.randint(0, len(participant_matches) - 1)]
            matches.append((participant, pot_match))
            """

        with open(self.results_file, "w+") as f:
            json.dump(matches, f)
        return matches
