#!/usr/bin/env python3
"""Build the Mongolian Latin plugin from a Mongolian word list.

The plugin turns a Latin word into Mongolian Cyrillic while you type. Its
rules and its idea of a spelling come from the maral keyboard project, and
the word list is ranked by how often each word appears in the corpus the
language pack was built from.

The words are stored in a compact code, one byte per letter, so the whole
dictionary fits inside Clink's plugin size limit.

Usage:
  python3 tools/build-mongolian-plugin.py --words source/mn.txt \
      --translit /path/to/translit.json --out Plugins/mongolian-latin.py
"""
import argparse
import json
import pathlib
import sys

# The compact code: one printable character per Mongolian letter. The code
# of a letter whose spelling never changes is the character of its own
# skeleton piece, so a word made only of those letters is its own skeleton
# and the plugin never has to walk it. The letters whose spelling does
# change are given the digits, and the digits are below "A", so a word that
# holds one of them is picked out with a single comparison.
CYR = "абвгдежзийклмнопрстуфхцчшщъыьэюяёүө"
LOW_CODES = "0123456789-."

HEADER = '''# ---
# name: Mongolian Latin
# icon: text.badge.checkmark
# summary: Type Mongolian in Latin letters and get Cyrillic
# version: 1.2
# author: cmspam
# ---

# Writes Mongolian in Cyrillic while you type Latin letters.
#
# Mongolian Cyrillic has letters Latin cannot express: the front rounded
# vowels ө and ү, the palatal series, and a soft sign that is usually left
# off the end of a word. So the conversion cannot be a fixed letter table.
# What it does instead:
#
#   * every Mongolian word is expanded into the spellings a typist might
#     use for it, so "ch" reaches ч, "shch" reaches щ and "u" can reach
#     either у or ү;
#   * the Latin you type is parsed the other way, into the same set of
#     spellings;
#   * the dictionary decides which word was meant, and its own frequency
#     breaks the remaining ties.
#
# The rules come from the maral keyboard project, which measured this
# spelling system over a 275 million token Mongolian corpus.
#
# It only writes Mongolian. Switch it off from the plugin's own settings, or
# leave the language alone and it stays out of the way.
'''


def check_quotes(text: str) -> None:
    """No quote character inside a triple-quoted string.

    Clink reads a triple-quoted string as ending at the first quote inside
    it, so a docstring that quotes a word leaves the rest of the file as
    rubbish and the app refuses the plugin. The words are named without
    quotes instead.
    """
    position = 0
    while True:
        start = text.find('"""', position)
        if start < 0:
            return
        end = text.find('"""', start + 3)
        if end < 0:
            raise SystemExit("A triple-quoted string was never closed.")
        body = text[start + 3:end]
        if '"' in body:
            raise SystemExit("A triple-quoted string holds a quote: " + body[:70])
        position = end + 3


def build_tables(translit: dict):
    """The code character of every letter, and the spellings it can take."""
    options = {}
    for letter in CYR:
        alts = translit["cyr"].get(letter) or [[letter, 0]]
        options[letter] = sorted((skeleton, int(cost)) for skeleton, cost in alts)
    after = {}
    for letter, alts in translit.get("cyr_after_vowel", {}).items():
        after[letter] = sorted((skeleton, int(cost)) for skeleton, cost in alts)

    # A letter whose spelling never changes takes the character of its own
    # piece as its code, so a word made only of those letters is its own
    # skeleton and the plugin never has to walk it. The letters whose piece
    # is more than one letter long cannot do that, because the skeleton
    # writes them as they are: "я" is "IA" and "иа" is "I" and "A", and
    # the two have to look the same to the word that means them.
    steady = [letter for letter in CYR
              if len(options[letter]) == 1 and letter not in after
              and len(options[letter][0][0]) == 1]
    loose = [letter for letter in CYR if letter not in steady]

    code = {}
    for letter in steady:
        code[letter] = options[letter][0][0]
    # The other letters take the digits and the marks below "A", so that a
    # word holding one of them is picked out with a single comparison.
    for index, letter in enumerate(loose):
        code[letter] = LOW_CODES[index]
    return code, options, after, steady, loose


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--words", required=True, help="word<TAB>count list, most frequent first")
    parser.add_argument("--translit", required=True, help="translit.json with the spelling rules")
    parser.add_argument("--out", required=True, help="plugin file to write")
    parser.add_argument("--limit", type=int, default=6000, help="how many words to carry")
    parser.add_argument("--name", default="Mongolian Latin", help="the name the plugin shows")
    arguments = parser.parse_args()

    translit = json.loads(pathlib.Path(arguments.translit).read_text(encoding="utf-8"))
    if set(translit["cyr"]) != set(CYR):
        raise SystemExit("The transliteration table and the compact code disagree about the alphabet.")
    code, options, after, steady, loose = build_tables(translit)
    if len(set(code.values())) != len(CYR):
        raise SystemExit("Two letters were given the same code character.")

    counts = []
    for line in pathlib.Path(arguments.words).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        word = fields[0]
        count = fields[1] if len(fields) > 1 else ""
        if not word or any(letter not in CYR for letter in word):
            continue
        try:
            frequency = int(count)
        except ValueError:
            frequency = 0
        if frequency <= 0:
            continue
        counts.append((word, frequency))
    counts.sort(key=lambda item: -item[1])
    counts = counts[: arguments.limit]
    if not counts:
        raise SystemExit("No usable words.")

    def encode(word: str) -> str:
        return "".join(code[letter] for letter in word)

    # The words go out as one string in a few long lines, so the file stays
    # well inside Clink's line limit. The separator is a bar rather than a
    # newline, because a newline inside the packed plugin is written as two
    # characters and the JSON that carries it doubles the backslash.
    chunks, current = [], ""
    for word, _ in counts:
        piece = encode(word) + "|"
        if len(current) + len(piece) > 1000:
            chunks.append(current)
            current = ""
        current += piece
    if current:
        chunks.append(current)
    literal = "\n".join(f'    "{chunk}",' for chunk in chunks)

    # The tables the plugin carries, keyed by the code character.
    letter_table = {code[letter]: letter for letter in CYR}
    alts = {}
    for letter in loose:
        alts[code[letter]] = list(options[letter])
    after_of = {}
    for letter, alts_list in after.items():
        after_of[code[letter]] = list(alts_list)
    vowels = set(translit["harmony"]["back"]) | set(translit["harmony"]["front"]) | set("иыю")
    vowel_codes = "".join(sorted(code[letter] for letter in vowels))
    cyr_vowels = "".join(sorted(vowels))

    # The Latin rules, with the pieces written as the characters of the
    # skeleton alphabet.
    latin = []
    for spelling, skeleton, cost in translit["latin"]:
        latin.append((spelling, skeleton, cost))
    # The hard sign is written with an apostrophe in the Latin spelling that
    # Mongolian typists use, so "yav'ya" means явъя. maral has no letter for
    # the sign, because it leaves signs off the end of words as a rule; the
    # sign that is written in the middle still has to be typed, so it takes
    # the same skeleton as "i" at a cost, and the fallback spelling writes ъ.
    latin.append(("'", "I", 3))

    body = f'''
CYR = "{CYR}"
LETTER = {letter_table!r}

# The other spellings of the letters whose spelling changes, and the change
# that happens after a vowel.
ALTS = {alts!r}
AFTER = {after_of!r}
VOWEL_CODES = "{vowel_codes}"
VOWELS = "{cyr_vowels}"


def _latin_rules(rules):
    """Latin spellings and their skeletons, grouped by first letter."""
    out = {{}}
    for spelling, skeleton, cost in rules:
        out.setdefault(spelling[0], []).append((spelling, skeleton, cost))
    for key in out:
        out[key] = sorted(out[key], key=lambda rule: (-len(rule[0]), rule[2]))
    return out


LATIN = _latin_rules({latin!r})

# The spelling of every Latin rule that has only one answer.
SPELLING = {{"a": "а", "b": "б", "ch": "ч", "d": "д", "e": "э", "f": "ф",
             "g": "г", "h": "х", "j": "ж", "k": "к", "kh": "х", "l": "л",
             "m": "м", "n": "н", "p": "п", "q": "ч", "r": "р", "s": "с",
             "sh": "ш", "shch": "щ", "t": "т", "ts": "ц", "v": "в", "w": "в",
             "ya": "я", "ye": "э", "yo": "ё", "yu": "ю", "z": "з", "zh": "ж",
             "'": "ъ"}}

INDEX = {{}}


def _log(value):
    """The natural logarithm, without the math module.

    The logarithm of a number near one is twice the arctangent series, and
    halving the number until it is near one keeps the series short.
    """
    count = 0
    while value > 2:
        value = value / 2
        count = count + 1
    ratio = (value - 1) / (value + 1)
    square = ratio * ratio
    total = ratio
    term = ratio
    power = 3
    while power < 25:
        term = term * square
        total = total + term / power
        power = power + 2
    return 2 * total + count * 0.693147180559945


def _spellings(record):
    """Every spelling of one word, cheapest first.

    A word is spelled by choosing one piece for each letter, and only the
    letters that can be spelled more than one way have a choice to make. The
    pieces are copied rather than rebuilt, so a word with a few loose letters
    stays cheap.
    """
    pieces = []
    spots = []
    previous = ""
    for character in record:
        if character < "A":
            # A letter whose spelling changes.
            options = ALTS[character]
            if previous in VOWEL_CODES and character in AFTER:
                options = AFTER[character]
            pieces.append(options[0][0])
            if len(options) > 1:
                spots.append((len(pieces) - 1, options))
        else:
            pieces.append(character)
        previous = character
    out = [(pieces, 0)]
    for position, options in spots:
        grown = []
        for base, cost in out:
            for piece, extra in options:
                copy = list(base)
                copy[position] = piece
                grown.append((copy, cost + extra))
        out = grown
    spellings = []
    for base, cost in out:
        spellings.append(("".join(base), cost))
    return spellings


def _parse(latin, beam):
    """Typed Latin to the spellings it might mean, cheapest first."""
    length = len(latin)
    paths = [{{}} for _ in range(length + 1)]
    paths[0][""] = 0
    for position in range(length):
        if not paths[position]:
            continue
        current = []
        for key in paths[position].keys():
            current.append((paths[position][key], key))
        current = sorted(current)[:beam]
        rules = LATIN.get(latin[position], [])
        if not rules:
            for cost, seen in current:
                key = seen + latin[position]
                if key not in paths[position + 1] or paths[position + 1][key] > cost:
                    paths[position + 1][key] = cost
            continue
        for rule, skeleton, rulecost in rules:
            if latin[position:position + len(rule)] != rule:
                continue
            target = position + len(rule)
            for cost, seen in current:
                key = seen + skeleton
                value = cost + rulecost + 1
                if key not in paths[target] or paths[target][key] > value:
                    paths[target][key] = value
    out = []
    for key in paths[length].keys():
        out.append((key, paths[length][key]))
    out = sorted(out, key=lambda item: (item[1], len(item[0]), item[0]))
    return out[:beam]


def _load():
    """Build the index: each word under every spelling that reaches it."""
    rank = 0
    for record in "".join(DATA).split("|"):
        if not record:
            continue
        if min(record) < "A":
            # The word holds a letter whose spelling changes, so it has more
            # than one skeleton.
            for skeleton, cost in _spellings(record):
                if skeleton not in INDEX:
                    INDEX[skeleton] = []
                INDEX[skeleton].append((record, cost, rank))
        else:
            # Every letter of the word keeps its own spelling, so the word
            # is its own skeleton.
            if record not in INDEX:
                INDEX[record] = []
            INDEX[record].append((record, 0, rank))
        rank = rank + 1


def _decode(record):
    """The compact code back to Mongolian."""
    word = ""
    for character in record:
        word = word + LETTER[character]
    return word


def _candidates(latin):
    """The words a typed Latin word might mean, best first."""
    _ready()
    parses = _parse(latin, 24)
    if parses:
        # The parses come back cheapest first, so the first one is the
        # cheapest and the rest are measured against it.
        cheapest = parses[0][1]
        parses = [(skeleton, cost - cheapest) for skeleton, cost in parses]
    out = []
    seen = {{}}
    for skeleton, parsecost in parses:
        for record, wordcost, rank in INDEX.get(skeleton, ()):
            if record in seen:
                continue
            seen[record] = True
            # The frequency term stands in for the corpus probability. It is
            # the rank, so the shape of the distribution is the corpus shape.
            score = 3.0 * parsecost + 3.0 * wordcost + 1.1 * _log(rank + 1)
            out.append((score, record))
    out = sorted(out, key=lambda item: (item[0], item[1]))
    if not out:
        guess = _spell(latin)
        if guess:
            return [guess]
        return []
    return [_decode(record) for _, record in out[:4]]


def _spell(latin):
    """Writes a word the dictionary does not have.

    The Latin is read rather than the dictionary's spelling space, so ia
    stays two letters and only ya becomes one letter. The rest comes from
    the corpus: an i after a vowel is the glide, a visible a is back, a
    visible e makes it front, and with neither it goes back, which is the
    commoner case.
    """
    tail = ""
    suffixes = [["guigeer", "гүйгээр"], ["guige", "гүйгэ"], ["gui", "гүй"]]
    for index in range(len(suffixes)):
        suffix = suffixes[index][0]
        cyrillic = suffixes[index][1]
        if len(latin) > len(suffix) and latin[len(latin) - len(suffix):] == suffix:
            tail = cyrillic
            latin = latin[: len(latin) - len(suffix)]
            break
    letters = []
    position = 0
    while position < len(latin):
        rule = ""
        if latin[position] in LATIN:
            candidates = LATIN[latin[position]]
        else:
            candidates = ()
        for candidate in candidates:
            if latin[position:position + len(candidate[0])] == candidate[0]:
                rule = candidate[0]
                break
        if not rule:
            position = position + 1
            continue
        letters.append(rule)
        position = position + len(rule)
    out = ""
    for rule in letters:
        previous = ""
        if out:
            previous = out[len(out) - 1]
        if rule == "i":
            if previous in VOWELS:
                out = out + "й"
            else:
                out = out + "и"
        elif rule == "y":
            if previous in VOWELS:
                out = out + "й"
            else:
                out = out + "ы"
        elif rule == "o":
            out = out + "o"
        elif rule == "u":
            out = out + "u"
        elif rule == "c":
            out = out + "ц"
        elif rule == "x":
            out = out + "ш"
        else:
            if rule in SPELLING:
                out = out + SPELLING[rule]
    front = False
    for character in out:
        if character == "а":
            front = False
            break
        if character == "э":
            front = True
            break
    if front:
        out = out.replace("o", "ө").replace("u", "ү")
    else:
        out = out.replace("o", "о").replace("u", "у")
    return out + tail


def _wanted(state):
    if not state.get("on", True):
        return False
    if state.get("always"):
        return True
    code = state.get("_language") or setting("language") or ""
    return code.startswith("mn")


def _ready():
    """Build the index the first time it is needed."""
    if not INDEX:
        _load()


def initial():
    return {{"on": True, "always": False}}


def on_language(code, state):
    state["_language"] = code
    return state


def settings(state):
    return section("text.corrections", [
        toggle("Write Mongolian in Cyrillic", state["on"], action="on"),
        toggle("Convert in every language", state["always"], action="always"),
    ], title="Mongolian Latin")


def on_action(action, value, state):
    if action in ("on", "always"):
        state[action] = value
    return state


def _ordinary(word):
    """Words worth rewriting: not a code, not an acronym, not a number."""
    if not word:
        return False
    # The hard sign is written with an apostrophe in Latin Mongolian typing,
    # so a word can carry one in the middle.
    letters = word.replace("'", "")
    if not letters or not letters.isalpha():
        return False
    for character in letters:
        # Only Latin letters. Anything else is left alone.
        if character < "A" or character > "z":
            return False
    if len(letters) > 1 and letters.isupper():
        return False
    return True


def suggestions(word, state):
    if not _ordinary(word) or not _wanted(state):
        return []
    return _candidates(word.lower())


def correct(word, fix, state):
    if not _ordinary(word) or not _wanted(state):
        return None
    candidates = _candidates(word.lower())
    if not candidates:
        return None
    return candidates[0]
'''

    text = HEADER.replace("# name: Mongolian Latin", f"# name: {arguments.name}") + body + f"\nDATA = (\n{literal}\n)\n"
    check_quotes(text)
    destination = pathlib.Path(arguments.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    size = destination.stat().st_size
    print(f"Wrote {destination}: {len(counts):,} words, {size:,} bytes.")


if __name__ == "__main__":
    main()
