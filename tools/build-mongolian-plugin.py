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

# The compact code: one printable character per Mongolian letter.
CYR = "абвгдежзийклмнопрстуфхцчшщъыьэюяёүө"
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345678"
assert len(CYR) == len(CODE) == 35, (len(CYR), len(CODE))

HEADER = '''# ---
# name: Mongolian Latin
# icon: textformat
# summary: Type Mongolian in Latin letters and get Cyrillic
# version: 1.0
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


def encode(word: str) -> str:
    return "".join(CODE[CYR.index(letter)] for letter in word)


def skeleton_table(translit: dict) -> str:
    """Cyrillic letter to the spellings it can take, as one string."""
    parts = []
    for letter in CYR:
        alternatives = translit["cyr"].get(letter)
        if alternatives is None:
            alternatives = [[letter, 0]]
        pieces = []
        for skeleton, cost in alternatives:
            pieces.append(("-" if skeleton == "" else skeleton) + str(cost))
        parts.append(letter + ":" + " ".join(pieces))
    return ";".join(parts)


def after_vowel_table(translit: dict) -> str:
    parts = []
    for letter, alternatives in translit.get("cyr_after_vowel", {}).items():
        pieces = [("-" if skeleton == "" else skeleton) + str(cost) for skeleton, cost in alternatives]
        parts.append(letter + ":" + " ".join(pieces))
    return ";".join(parts)


def latin_table(translit: dict) -> str:
    rules = [f"{latin}:{skeleton}{cost}" for latin, skeleton, cost in translit["latin"]]
    # The hard sign is written with an apostrophe in the Latin spelling that
    # Mongolian typists use, so "yav'ya" means явъя. maral has no letter for
    # the sign, because it leaves signs off the end of words as a rule; the
    # sign that is written in the middle still has to be typed, so it takes
    # the same skeleton as "i" at a cost, and the fallback spelling writes ъ.
    rules.append("':I3")
    return " ".join(rules)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--words", required=True, help="word<TAB>count list, most frequent first")
    parser.add_argument("--translit", required=True, help="translit.json with the spelling rules")
    parser.add_argument("--out", required=True, help="plugin file to write")
    parser.add_argument("--limit", type=int, default=6000, help="how many words to carry")
    arguments = parser.parse_args()

    translit = json.loads(pathlib.Path(arguments.translit).read_text(encoding="utf-8"))
    if set(translit["cyr"]) != set(CYR):
        raise SystemExit("The transliteration table and the compact code disagree about the alphabet.")
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

    data = "".join(encode(word) + "\\n" for word, _ in counts)
    # The words go out as escaped newlines, in a few long lines, so the file
    # stays well inside Clink's line limit.
    chunks, current = [], ""
    for word in counts:
        piece = encode(word[0]) + "\\n"
        if len(current) + len(piece) > 1000:
            chunks.append(current)
            current = ""
        current += piece
    if current:
        chunks.append(current)
    literal = "\n".join(f'    "{chunk}"' for chunk in chunks)
    vowels = "".join(sorted(set(translit["harmony"]["back"]) | set(translit["harmony"]["front"]) | set("иыю")))

    body = f'''
import math

CYR = "{CYR}"
CODE = "{CODE}"
LETTER = {{}}
for position in range(len(CODE)):
    LETTER[CODE[position]] = CYR[position]
VOWELS = "{vowels}"


def _parse_pairs(spec):
    """letter:SPELLING COST SPELLING COST; into a lookup."""
    out = {{}}
    for part in spec.split(";"):
        if not part:
            continue
        letter, alternatives = part.split(":")
        out[letter] = []
        for item in alternatives.split():
            out[letter].append(("" if item[:-1] == "-" else item[:-1], int(item[-1])))
    return out


COLLAPSE = _parse_pairs("{skeleton_table(translit)}")
AFTER = _parse_pairs("{after_vowel_table(translit)}")


def _latin_rules(spec):
    """latin:SPELLING COST, grouped by first letter, longest match first."""
    out = {{}}
    for part in spec.split():
        latin, rest = part.split(":")
        out.setdefault(latin[0], []).append((latin, rest[:-1], int(rest[-1])))
    for key in out:
        out[key].sort(key=lambda rule: (-len(rule[0]), rule[2]))
    return out


LATIN = _latin_rules("{latin_table(translit)}")

# The spelling of every Latin rule that has only one answer.
SPELLING = {{"a": "а", "b": "б", "ch": "ч", "d": "д", "e": "э", "f": "ф",
             "g": "г", "h": "х", "j": "ж", "k": "к", "kh": "х", "l": "л",
             "m": "м", "n": "н", "p": "п", "q": "ч", "r": "р", "s": "с",
             "sh": "ш", "shch": "щ", "t": "т", "ts": "ц", "v": "в", "w": "в",
             "ya": "я", "ye": "э", "yo": "ё", "yu": "ю", "z": "з", "zh": "ж",
             "'": "ъ"}}

WORDS = []
INDEX = {{}}


def _expand(word, cap):
    """Every spelling of one Mongolian word, cheapest first."""
    out = [("", 0)]
    for position in range(len(word)):
        letter = word[position]
        if position and word[position - 1] in VOWELS and letter in AFTER:
            alternatives = AFTER[letter]
        else:
            alternatives = COLLAPSE.get(letter, [(letter, 0)])
        if len(alternatives) == 1:
            skeleton, cost = alternatives[0]
            out = [(seen + skeleton, total + cost) for seen, total in out]
        else:
            grown = []
            for seen, total in out:
                for skeleton, cost in alternatives:
                    grown.append((seen + skeleton, total + cost))
            grown.sort(key=lambda item: item[1])
            out = grown[:cap]
    return out


def _parse(latin, beam):
    """Typed Latin to the spellings it might mean, cheapest first."""
    length = len(latin)
    paths = [{{}} for _ in range(length + 1)]
    paths[0][""] = 0
    for position in range(length):
        if not paths[position]:
            continue
        current = sorted(paths[position].items(), key=lambda item: (item[1], item[0]))[:beam]
        rules = LATIN.get(latin[position], [])
        if not rules:
            for seen, cost in current:
                key = seen + latin[position]
                if key not in paths[position + 1] or paths[position + 1][key] > cost:
                    paths[position + 1][key] = cost
            continue
        for rule, skeleton, rulecost in rules:
            if not latin.startswith(rule, position):
                continue
            target = position + len(rule)
            for seen, cost in current:
                key = seen + skeleton
                value = cost + rulecost + 1
                if key not in paths[target] or paths[target][key] > value:
                    paths[target][key] = value
    out = sorted(paths[length].items(), key=lambda item: (item[1], len(item[0]), item[0]))
    return out[:beam]


def _load():
    """Build the index: each word under every spelling that reaches it."""
    for rank, record in enumerate(DATA.split("\\n")):
        if not record:
            continue
        word = ""
        for character in record:
            word += LETTER[character]
        WORDS.append(word)
        for skeleton, cost in _expand(word, 12):
            if skeleton not in INDEX:
                INDEX[skeleton] = []
            INDEX[skeleton].append((word, cost, rank))


def _candidates(latin):
    """The words a typed Latin word might mean, best first."""
    parses = _parse(latin, 24)
    if parses:
        cheapest = min(cost for _, cost in parses)
        parses = [(skeleton, cost - cheapest) for skeleton, cost in parses]
    out = []
    seen = {{}}
    for skeleton, parsecost in parses:
        for word, wordcost, rank in INDEX.get(skeleton, ()):
            if word in seen:
                continue
            seen[word] = True
            # The frequency term stands in for the corpus probability. It is
            # the rank, so the shape of the distribution is the corpus shape.
            score = 3.0 * parsecost + 3.0 * wordcost + 1.1 * math.log(rank + 1)
            out.append((score, word))
    out.sort(key=lambda item: (item[0], item[1]))
    if not out:
        guess = _spell(latin)
        if guess:
            out.append((0.0, guess))
    return [word for _, word in out[:4]]


def _spell(latin):
    """A word the dictionary does not have still gets written in Cyrillic.

    This reads the Latin rather than the dictionary's spelling space, so "ia"
    stays two letters and only "ya" becomes я. The remaining guesses come
    from the corpus: an и straight after a vowel is the glide й, a word with
    a visible а is back, a visible э makes it front, and with neither it
    goes back, which is the commoner case.
    """
    tail = ""
    for suffix, cyrillic in (("guigeer", "гүйгээр"), ("guige", "гүйгэ"), ("gui", "гүй")):
        if len(latin) > len(suffix) and latin.endswith(suffix):
            tail = cyrillic
            latin = latin[: len(latin) - len(suffix)]
            break
    letters = []
    position = 0
    while position < len(latin):
        rule = None
        for candidate in LATIN.get(latin[position], ()):
            if latin.startswith(candidate[0], position):
                rule = candidate[0]
                break
        if rule is None:
            position += 1
            continue
        letters.append(rule)
        position += len(rule)
    out = ""
    for rule in letters:
        previous = out[-1] if out else ""
        if rule == "i":
            out += "й" if previous in VOWELS else "и"
        elif rule == "y":
            out += "й" if previous in VOWELS else "ы"
        elif rule == "o":
            out += "o"
        elif rule == "u":
            out += "u"
        elif rule == "c":
            out += "ц"
        elif rule == "x":
            out += "ш"
        else:
            out += SPELLING.get(rule, "")
    front = False
    for character in out:
        if character == "а":
            front = False
            break
        if character == "э":
            front = True
            break
    out = out.replace("o", "ө" if front else "о").replace("u", "ү" if front else "у")
    return out + tail


def _wanted(state):
    if not state.get("on", True):
        return False
    if state.get("always"):
        return True
    code = state.get("_language") or setting("language") or ""
    return code.startswith("mn")


def initial():
    _load()
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
    if not word or not word.isascii():
        return False
    # The hard sign is written with an apostrophe in Latin Mongolian typing,
    # so a word can carry one in the middle.
    letters = word.replace("'", "")
    if not letters or not letters.isalpha():
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

    text = HEADER + body + f"\nDATA = (\n{literal}\n)\n"
    destination = pathlib.Path(arguments.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    size = destination.stat().st_size
    print(f"Wrote {destination}: {len(counts):,} words, {size:,} bytes.")


if __name__ == "__main__":
    main()
