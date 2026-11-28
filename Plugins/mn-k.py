# ---
# name: Mongolian Latin Test K
# icon: text.badge.checkmark
# summary: The fallback with a plain English docstring
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

CYR = "абвгдежзийклмнопрстуфхцчшщъыьэюяёүө"
LETTER = {'A': 'а', 'B': 'б', '0': 'в', 'G': 'г', 'D': 'д', '1': 'е', 'J': 'ж', 'Z': 'з', 'I': 'и', '2': 'й', 'K': 'к', 'L': 'л', 'M': 'м', 'N': 'н', 'O': 'о', 'P': 'п', 'R': 'р', 'S': 'с', 'T': 'т', 'U': 'у', 'F': 'ф', 'H': 'х', 'C': 'ц', 'Q': 'ч', 'X': 'ш', '3': 'щ', '4': 'ъ', '5': 'ы', '6': 'ь', 'E': 'э', '7': 'ю', '8': 'я', '9': 'ё', '-': 'ү', '.': 'ө'}

# The other spellings of the letters whose spelling changes, and the change
# that happens after a vowel.
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
SPELLING = {"a": "а", "b": "б", "ch": "ч", "d": "д", "e": "э", "f": "ф",
             "g": "г", "h": "х", "j": "ж", "k": "к", "kh": "х", "l": "л",
             "m": "м", "n": "н", "p": "п", "q": "ч", "r": "р", "s": "с",
             "sh": "ш", "shch": "щ", "t": "т", "ts": "ц", "v": "в", "w": "в",
             "ya": "я", "ye": "э", "yo": "ё", "yu": "ю", "z": "з", "zh": "ж",
             "'": "ъ"}

INDEX = {}


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
    paths = [{} for _ in range(length + 1)]
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
    seen = {}
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
    """A word the dictionary does not have still gets written in Cyrillic.

    This reads the Latin rather than the dictionary's spelling space, so ia
    stays two letters and only ya becomes one letter. The remaining guesses come
    from the corpus: an i after a vowel is the glide, a word with
    a visible a is back, a visible e makes it front, and with neither it
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
            if latin[position:position + len(candidate[0])] == candidate[0]:
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


def _ready():
    """Build the index the first time it is needed."""
    if not INDEX:
        _load()


def initial():
    return {"on": True, "always": False}


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

DATA = (
    "N6|BA2NA|7M|ENE|Q|BA2GAA|GEJ|L|BOLON|ULS5N|BA2SAN|BOL|IH|NEG|OLON|MONGOL|ON5|H-N|SAR5N|OND|BA2H|BA2DAG|DEER|GESEN|B.G..D|ULS|BOLNO|TER|M.N|TUHA2|HAMGI2N|CAG|BOLSON|-2L|GAZAR|HO9R|TUS|BI|ZASGI2N|T.RI2N|8MAR|BOLOH|TA|BOLJ|BU2|-1D|BA|BID|DAH6|GEDEG|GAZR5N|HARIN|0E|UU|DARGA|SA2N|TALAAR|JILI2N|DARAA|XINE|.MN.|H-NI2|MONGOL5N|AJ|A0Q|ZOHION|ORON|ERH|B-H|A2MGI2N|BU7U|.D.R|HI2J|ARGA|JIL|ZEREG|DUGAAR|DELHI2N|NAR|MANA2|HUUL6|ALBAN|HUULI2N|BIX|T--NI2|AJIL|DEE|BI2|1R.NHI2|HEREGTE2|-R|7U|EDI2N|BUSAD|HU06D|MAX|A0AH|AJL5N|Z-2L|GEH|NER|9STO2|SA8|HI2H|SA2D|BA2J|H-M--S|AJILLAJ|X--|EH|GEED|..RI2N|ODOO|IL--|..R|.ND.R|ER--L|BAGA|HU06|TOM|NEGEN|BAS|I2M|XIG|T.0|BILEE|B-R|GOL|NI2T|MEDEELEL|-NDESNI2|H-RTEL|-NDSEN|B|SANAL|ZARIM|ZASAG|BA20|BUTLUUR|ES0EL|UG|HOT5N|TUHA2N|HEREG|MAXIN|ENEH--|TULD|GER|DAHIN|UDAA|-G|HEDEN|GEHDEE|D|HEMEEN|B-HI2|BUS|DEED|A0SAN|ASUUDAL|HI2SEN|IRSEN|B-REN|.N..D.R|SA2HAN|ARD|MINI2|GIX--N|DUND|ULSAD|BOLOMJTO2|GARU2|BA2DAL|TED|H.R.NG.|DAGUU|NUTGI2N|UUL|AJILLAGAA|BA2LAA|QIN6|UQIR|BI1|-1I2N|-NE|",
    "GEDGI2G|QUHAL|H-ND|GARQ|NI2GMI2N|HESEG|GUR0AN|TEREER|H--HED|NI2SLELI2N|HERHEN|HEN|ZAM|MET|UURHA2N|HUGACAAND|RUU|SAR|TODORHO2|--|H-LEEN|TUL|Z.0H.N|SUM5N|AL6|GADAAD|Z.0|HAMT|ORJ|HEMJEE|ANHN5|SURGUULI2N|TAN5|H.GJLI2N|SURGUUL6|T--NI2G|URAN|.NG.RS.N|TI2M|GADNA|GAR|NAS|BA2HG-2|BAGX|HOLBOOTO2|SETGEL|TONOG|QULUU|HO2X|SARD|Z-2N|HOT|.DRI2N|BA2R|AJILLAH|UQRAAS|1R.NHI2L.GQ|ULAANBAATAR|MERGEJLI2N|M8NGAN|BA2JEE|ZAH|HAMTRAN|BA2DLAAR|T.RLI2N|MAAN6|NAR5N|TI2MEES|ANH|HU0I2N|BA2GUULLAGA|H--HDI2N|HEMJEENI2|GARSAN|-1|H-REEND|DAA|ASUUDL5G|D-GEER|S--LI2N|GARGASAN|CAGAAN|M.NG.|EDGEER|NUTAG|AM|BIDNI2|-2LD0ER|KOMPANI|CERGI2N|XAARDLAGATA2|DED|T.L..|ZURAG|DOTOR|GARGAJ|CAHIM|TAL|MEDEELLI2N|S|MEDEE|ZAM5N|HAR|TERBUM|--NI2G|AJL5G|TUSGA2|BOLJEE|T.R|HOTOD|AHU2N|BOLO0Q|NI2TI2N|H8TAD|DEH|H-QIN|BARUUN|.GS.N|8G|TEDNI2|..R..|AJILLAGAAN5|IRGED|A7ULG-2|T.H..R.MJ|MIN6|ORQIN|N|HEL|BE|ESREG|T.S.L|XUUD|BA2HAD|BA2GUULLAG5N|ONOOS|HAMGAALAH|TOO|D--RGI2N|ORN5|BA2GAAG|.MN.D|EHNI2|.RG.N|G|-2LD0ERI2N|JIJIG|.MN.H|ON|HAAN|-1ER|IRGEDI2N|",
    "IREH|Z--N|NEGDSEN|BOLOOD|HERGI2N|--REG|DEERH|MENDI2N|ORQIM|BOLGON|ZALUU|XILDEG|B-RI2N|EHELSEN|IRGEN|T.RS.N|BOLO0|BOLLOO|NARI2N|GENE|CAHILGAAN|BA2GUULAH|GETEL|ED|H8TAD5N|BA2DL5G|BOLDOG|8AGAAD|OLJ|NAM5N|BOLGOH|.G.H|XI2D0ER|80J|B-GD|HEMJEEND|US|TEE0RI2N|N.HC.L|HURL5N|H-QNI2|AJILLAGAAG|HOROON5|BOLOMJ|BOLGOJ|QI|BOLOHG-2|BUTLUUR5N|X--H|BA2DL5N|TEGEED|XINJLEH|END|CAGT|..RQL.LT|-2LQILGEE|BARILG5N|HOLBOGDOH|T.GR.G|HERE0|QADAHG-2|KINO|A0ARGA|IRJ|OROS5N|MINUT|HELJ|UHAAN5|HOLBOON5|SANH--GI2N|TOHIOLDOLD|HUDALDAN|H--|TA0AN|HED|.GQ|-ZEJ|BOLO0SRUULAH|ZEELI2N|AGAAR5N|CAGI2N|ZEEL|H-M--SI2N|EMEGTE2|BOLOHOOR|B-TEEGDEH--N|MEDEELLI2G|HOOROND|KOMPANI2N|80DAL|DUU|BA2GAAD|GE0Q|BODLOGO|BA2GUULJ|BAG|GANC|H-Q|BOLO0SROL5N|..RI2G..|GARGAH|C|--NI2|ONCGO2|-NEN|ORSON|IRGENI2|HONOGI2N|D.R0.N|SANAA|T.M.R|DARAAH|SALBAR5N|A2MAG|ECEG|8AJ|HUGACAA|BA2GUULSAN|GEMT|1R|GEHED|HOLBOO|ERQIM|XATN5|MONGOLD|BIQIG|SALBAR|HO2D|NAM|M|NEMELT|T.SLI2N|X--HI2N|MUU|HARJ|DARG5N|SAN|BA2GAL6|A|DELHI2|J|HOOL|NASN5|Z-2LI2N|ZAHIRGAAN5|BA8R|DOLOO|",
    "IL|BARIMT|HESEGT|URT|HAMT5N|ULAAN|--NEES|GEREE|TERBEER|BUTLAH|NASTA2|H-NI2G|ORUULAH|-L|-G-2|NOM|",
)
