#!/usr/bin/env python3
"""Measure the Mongolian Latin plugin the way maral measures its engine.

Held-out Cyrillic sentences are typed in Latin with maral's own spec-mode
typist, then the plugin's suggestions are compared with the reference words.

Usage: python3 tools/measure-mongolian-plugin.py [--limit N] [--plugin PATH]
"""
import argparse
import collections
import gzip
import importlib.util
import pathlib
import random
import sys

HOLDOUT = "/home/charlesmiller/Development/Claude/maral/data/derived/holdout.txt.gz"
"""Where the held-out Cyrillic sentences live. Point --holdout somewhere else."""

SPEC = {
    'х': [('h', 8), ('kh', 2)],
    'ч': [('ch', 7), ('q', 3)],
    'ш': [('sh', 7), ('x', 3)],
    'ц': [('ts', 7), ('c', 3)],
    'ж': [('j', 10)],
    'з': [('z', 10)],
    'ы': [('ii', 6), ('y', 4)],
    'ь': [('i', 6), ('', 4)],
    'ъ': [('i', 5), ('', 5)],
    'е': [('e', 9), ('ye', 1)],
    'ё': [('yo', 10)],
    'ю': [('yu', 10)],
    'я': [('ya', 10)],
    'й': [('i', 6), ('y', 4)],
    'в': [('v', 10)],
    'щ': [('shch', 10)],
    'ө': [('o', 5), ('u', 5)],
    'ү': [('u', 10)],
}
FIXED = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
         'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm',
         'н': 'n', 'о': 'o', 'ө': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
         'у': 'u', 'ү': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh',
         'щ': 'shch', 'ъ': 'i', 'ь': 'i', 'ы': 'ii', 'э': 'e', 'ю': 'yu', 'я': 'ya'}


def pick(rng, options):
    total = sum(weight for _, weight in options)
    value = rng.uniform(0, total)
    for spelling, weight in options:
        value -= weight
        if value <= 0:
            return spelling
    return options[-1][0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=2000, help="sentences to test")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--plugin", default="Plugins/mongolian-latin.py")
    parser.add_argument("--skip", type=int, default=0, help="skip this many sentences first")
    parser.add_argument("--holdout", default=HOLDOUT, help="held-out sentences, one per line")
    arguments = parser.parse_args()

    module = importlib.util.spec_from_file_location("mongolian_latin", arguments.plugin)
    plugin = importlib.util.module_from_spec(module)
    module.loader.exec_module(plugin)
    plugin.setting = lambda name: "mn"
    state = plugin.initial()
    state["always"] = True

    rng = random.Random(arguments.seed)
    known = set(plugin.WORDS)
    total = correct = 0
    known_total = known_correct = 0
    missed = collections.Counter()
    example = []
    with gzip.open(arguments.holdout, "rt", encoding="utf-8") as handle:
        sentences = 0
        for number, line in enumerate(handle):
            if number < arguments.skip:
                continue
            if sentences >= arguments.limit:
                break
            sentences += 1
            words = line.split()
            choices = {letter: pick(rng, options) for letter, options in SPEC.items()}
            for word in words:
                typed = "".join(
                    choices.get(letter, FIXED.get(letter, letter))
                    for letter in word.lower()
                )
                if not typed or not typed.isalpha():
                    continue
                got = plugin.suggestions(typed, state)
                top = got[0] if got else None
                total += 1
                if top == word:
                    correct += 1
                else:
                    missed[(word, typed, top)] += 1
                    if len(example) < 15:
                        example.append((typed, word, top))
                if word in known:
                    known_total += 1
                    if top == word:
                        known_correct += 1

    print(f"words tested           {total:,}")
    print(f"word accuracy          {correct / total * 100:.2f}%")
    if known_total:
        print(f"in-dictionary accuracy  {known_correct / known_total * 100:.2f}%  "
              f"({known_total:,} of {total:,} words were in the dictionary)")
    print()
    for typed, word, top in example:
        print(f"  {typed:<22} -> {str(top):<20} want {word}")


if __name__ == "__main__":
    main()
