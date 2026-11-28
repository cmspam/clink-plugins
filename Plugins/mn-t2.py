# ---
# name: Mongolian Latin Test 2
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

DATA = (
    "N6|BA2NA|7M|ENE|Q|BA2GAA|GEJ|L|BOLON|ULS5N|BA2SAN|BOL|IH|NEG|OLON|MONGOL|ON5|H-N|SAR5N|OND|BA2H|BA2DAG|DEER|GESEN|B.G..D|ULS|BOLNO|TER|M.N|TUHA2|HAMGI2N|CAG|BOLSON|-2L|GAZAR|HO9R|TUS|BI|ZASGI2N|T.RI2N|8MAR|BOLOH|TA|BOLJ|BU2|-1D|BA|BID|DAH6|GEDEG|GAZR5N|HARIN|0E|UU|DARGA|SA2N|TALAAR|JILI2N|DARAA|XINE|.MN.|H-NI2|MONGOL5N|AJ|A0Q|ZOHION|ORON|ERH|B-H|A2MGI2N|BU7U|.D.R|HI2J|ARGA|JIL|ZEREG|DUGAAR|DELHI2N|NAR|MANA2|HUUL6|ALBAN|HUULI2N|BIX|T--NI2|AJIL|DEE|BI2|1R.NHI2|HEREGTE2|-R|7U|EDI2N|BUSAD|HU06D|MAX|A0AH|AJL5N|Z-2L|GEH|NER|9STO2|SA8|HI2H|SA2D|BA2J|H-M--S|AJILLAJ|X--|EH|GEED|..RI2N|ODOO|IL--|..R|.ND.R|ER--L|BAGA|HU06|TOM|NEGEN|BAS|I2M|XIG|T.0|BILEE|B-R|GOL|NI2T|MEDEELEL|-NDESNI2|H-RTEL|-NDSEN|B|SANAL|ZARIM|ZASAG|BA20|BUTLUUR|ES0EL|UG|HOT5N|TUHA2N|HEREG|MAXIN|ENEH--|TULD|GER|DAHIN|UDAA|-G|HEDEN|GEHDEE|D|HEMEEN|B-HI2|BUS|DEED|A0SAN|ASUUDAL|HI2SEN|IRSEN|B-REN|.N..D.R|SA2HAN|ARD|MINI2|GIX--N|DUND|ULSAD|BOLOMJTO2|GARU2|BA2DAL|TED|H.R.NG.|DAGUU|NUTGI2N|UUL|AJILLAGAA|BA2LAA|QIN6|UQIR|BI1|-1I2N|-NE|",
    "GEDGI2G|QUHAL|H-ND|GARQ|NI2GMI2N|HESEG|GUR0AN|TEREER|H--HED|NI2SLELI2N|HERHEN|HEN|ZAM|MET|UURHA2N|HUGACAAND|RUU|SAR|TODORHO2|--|H-LEEN|TUL|Z.0H.N|SUM5N|AL6|GADAAD|Z.0|HAMT|ORJ|HEMJEE|ANHN5|SURGUULI2N|TAN5|H.GJLI2N|SURGUUL6|T--NI2G|URAN|.NG.RS.N|TI2M|GADNA|GAR|NAS|BA2HG-2|BAGX|HOLBOOTO2|SETGEL|TONOG|QULUU|HO2X|SARD|Z-2N|HOT|.DRI2N|BA2R|AJILLAH|UQRAAS|1R.NHI2L.GQ|ULAANBAATAR|MERGEJLI2N|M8NGAN|BA2JEE|ZAH|HAMTRAN|BA2DLAAR|T.RLI2N|MAAN6|NAR5N|TI2MEES|ANH|HU0I2N|BA2GUULLAGA|H--HDI2N|HEMJEENI2|GARSAN|-1|H-REEND|DAA|ASUUDL5G|D-GEER|S--LI2N|GARGASAN|CAGAAN|M.NG.|EDGEER|NUTAG|AM|BIDNI2|-2LD0ER|KOMPANI|CERGI2N|XAARDLAGATA2|DED|T.L..|ZURAG|DOTOR|GARGAJ|CAHIM|TAL|MEDEELLI2N|S|MEDEE|ZAM5N|HAR|TERBUM|--NI2G|AJL5G|TUSGA2|BOLJEE|T.R|HOTOD|AHU2N|BOLO0Q|NI2TI2N|H8TAD|DEH|H-QIN|BARUUN|.GS.N|8G|TEDNI2|..R..|AJILLAGAAN5|IRGED|A7ULG-2|T.H..R.MJ|MIN6|ORQIN|N|HEL|BE|ESREG|T.S.L|XUUD|BA2HAD|BA2GUULLAG5N|ONOOS|HAMGAALAH|TOO|D--RGI2N|ORN5|BA2GAAG|.MN.D|EHNI2|.RG.N|G|-2LD0ERI2N|JIJIG|.MN.H|ON|HAAN|-1ER|IRGEDI2N|",
    "IREH|Z--N|NEGDSEN|BOLOOD|HERGI2N|--REG|DEERH|MENDI2N|ORQIM|BOLGON|ZALUU|XILDEG|B-RI2N|EHELSEN|IRGEN|T.RS.N|BOLO0|BOLLOO|NARI2N|GENE|CAHILGAAN|BA2GUULAH|GETEL|ED|H8TAD5N|BA2DL5G|BOLDOG|8AGAAD|OLJ|NAM5N|BOLGOH|.G.H|XI2D0ER|80J|B-GD|HEMJEEND|US|TEE0RI2N|N.HC.L|HURL5N|H-QNI2|AJILLAGAAG|HOROON5|BOLOMJ|BOLGOJ|QI|BOLOHG-2|BUTLUUR5N|X--H|BA2DL5N|TEGEED|XINJLEH|END|CAGT|..RQL.LT|-2LQILGEE|BARILG5N|HOLBOGDOH|T.GR.G|HERE0|QADAHG-2|KINO|A0ARGA|IRJ|OROS5N|MINUT|HELJ|UHAAN5|HOLBOON5|SANH--GI2N|TOHIOLDOLD|HUDALDAN|H--|TA0AN|HED|.GQ|-ZEJ|BOLO0SRUULAH|ZEELI2N|AGAAR5N|CAGI2N|ZEEL|H-M--SI2N|EMEGTE2|BOLOHOOR|B-TEEGDEH--N|MEDEELLI2G|HOOROND|KOMPANI2N|80DAL|DUU|BA2GAAD|GE0Q|BODLOGO|BA2GUULJ|BAG|GANC|H-Q|BOLO0SROL5N|..RI2G..|GARGAH|C|--NI2|ONCGO2|-NEN|ORSON|IRGENI2|HONOGI2N|D.R0.N|SANAA|T.M.R|DARAAH|SALBAR5N|A2MAG|ECEG|8AJ|HUGACAA|BA2GUULSAN|GEMT|1R|GEHED|HOLBOO|ERQIM|XATN5|MONGOLD|BIQIG|SALBAR|HO2D|NAM|M|NEMELT|T.SLI2N|X--HI2N|MUU|HARJ|DARG5N|SAN|BA2GAL6|A|DELHI2|J|HOOL|NASN5|Z-2LI2N|ZAHIRGAAN5|BA8R|DOLOO|",
    "IL|BARIMT|HESEGT|URT|HAMT5N|ULAAN|--NEES|GEREE|TERBEER|BUTLAH|NASTA2|H-NI2G|ORUULAH|-L|-G-2|NOM|",
)
