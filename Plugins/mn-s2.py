# ---
# name: Mongolian Latin Step 2
# icon: text.badge.checkmark
# summary: Type Mongolian in Latin letters and get Cyrillic
# version: 1.1
# author: cmspam
# ---

# Suggestions and corrections of your own.
#
# suggestions(word, state) runs as you type and returns words for the bar,
# ahead of the keyboard's own. word is the one being typed, empty between
# words; context() has the text around it.
#
# correct(word, fix, state) runs when space ends a word. fix is what the
# keyboard was about to change it to, or None. Return a word to commit that
# instead, False to leave the word exactly as typed, or None to let the
# keyboard decide. Backspace right after still undoes it, like any
# autocorrect.
#
# Shorthand offers the expansion of a few abbreviations while you type them,
# expands them on space if you want, and keeps autocorrect off words in capitals
# and words with digits in them.
SHORT = {
    "brb": "be right back",
    "omw": "on my way",
    "idk": "I don't know",
    "tbh": "to be honest",
    "afaik": "as far as I know",
    "imo": "in my opinion",
}

def initial():
    return {"expand": False, "guard": True}

def settings(state):
    return section("text.corrections", [
        toggle("Expand shorthand on space", state["expand"], action="expand"),
        toggle("Leave capitals and numbers alone", state["guard"], action="guard"),
    ], title="Shorthand")

def on_action(action, value, state):
    if action in ("expand", "guard"):
        state[action] = value
    return state

def suggestions(word, state):
    long = SHORT.get(word.lower())
    return [long] if long else []

def correct(word, fix, state):
    long = SHORT.get(word.lower())
    if long and state["expand"]:
        return long
    if state["guard"]:
        if len(word) > 1 and word.isupper():
            return False
        if any(c.isdigit() for c in word):
            return False
    return None

CYR = "абвгдежзийклмнопрстуфхцчшщъыьэюяёүө"
LETTER = {'A': 'а', 'B': 'б', '0': 'в', 'G': 'г', 'D': 'д', '1': 'е', 'J': 'ж', 'Z': 'з', 'I': 'и', '2': 'й', 'K': 'к', 'L': 'л', 'M': 'м', 'N': 'н', 'O': 'о', 'P': 'п', 'R': 'р', 'S': 'с', 'T': 'т', 'U': 'у', 'F': 'ф', 'H': 'х', 'C': 'ц', 'Q': 'ч', 'X': 'ш', '3': 'щ', '4': 'ъ', '5': 'ы', '6': 'ь', 'E': 'э', '7': 'ю', '8': 'я', '9': 'ё', '-': 'ү', '.': 'ө'}

# The other spellings of the letters whose spelling changes, and the change
# that happens after a vowel.
VOWEL_CODES = "-.15789AEIOU"
VOWELS = "аеиоуыэюяёүө"


SPELLING = {"a": "а", "b": "б", "ch": "ч", "d": "д", "e": "э", "f": "ф",
             "g": "г", "h": "х", "j": "ж", "k": "к", "kh": "х", "l": "л",
             "m": "м", "n": "н", "p": "п", "q": "ч", "r": "р", "s": "с",
             "sh": "ш", "shch": "щ", "t": "т", "ts": "ц", "v": "в", "w": "в",
             "ya": "я", "ye": "э", "yo": "ё", "yu": "ю", "z": "з", "zh": "ж",
             "'": "ъ"}

ALTS = {'0': [('V', 0), ('W', 2)], '1': [('E', 0), ('IE', 1)], '2': [('I', 0)], '3': [('X', 0), ('XQ', 1)], '4': [('', 1), ('I', 0)], '5': [('I', 3), ('II', 0), ('Y', 0)], '6': [('', 1), ('I', 0)], '7': [('IU', 0)], '8': [('IA', 0)], '9': [('IO', 0)], '-': [('O', 2), ('U', 0)], '.': [('O', 0), ('U', 1)]}
AFTER = {'2': [('I', 0), ('Y', 0)]}
VOWEL_CODES = "-.15789AEIOU"
VOWELS = "аеиоуыэюяёүө"


def _latin_rules(rules):
    """Latin spellings and their skeletons, grouped by first letter."""
    out = {}
    for spelling, skeleton, cost in rules:
        out.setdefault(spelling[0], []).append((spelling, skeleton, cost))
    for key in out:
        out[key] = sorted(out[key], key=lambda rule: (-len(rule[0]), rule[2]))
    return out


LATIN = _latin_rules([('yu', 'IU', 0), ('yo', 'IO', 0), ('ye', 'IE', 0), ('ya', 'IA', 0), ('shch', 'X', 0), ('ch', 'Q', 0), ('sh', 'X', 0), ('ts', 'C', 0), ('kh', 'H', 0), ('zh', 'J', 0), ('a', 'A', 0), ('b', 'B', 0), ('v', 'V', 0), ('g', 'G', 0), ('d', 'D', 0), ('e', 'E', 0), ('j', 'J', 0), ('z', 'Z', 0), ('i', 'I', 0), ('k', 'K', 0), ('l', 'L', 0), ('m', 'M', 0), ('n', 'N', 0), ('o', 'O', 0), ('p', 'P', 0), ('r', 'R', 0), ('s', 'S', 0), ('t', 'T', 0), ('u', 'U', 0), ('f', 'F', 0), ('h', 'H', 0), ('q', 'Q', 0), ('x', 'X', 0), ('c', 'C', 0), ('x', 'H', 3), ('c', 'K', 3), ('c', 'S', 4), ('w', 'V', 2), ('y', 'Y', 0), ('y', 'I', 2), ("'", 'I', 3)])

# The spelling of every Latin rule that has only one answer.
