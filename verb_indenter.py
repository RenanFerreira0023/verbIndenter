from __future__ import annotations

"""Web-based business rules for English verb lookup and suggestion."""

import json
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Verb:
    infinitive: str
    simple_past: str
    participle: str
    kind: str
    definition: str = ""
    source: str = "Wiktionary"


@dataclass(frozen=True)
class WiktionaryVerbEntry:
    word: str
    wikitext: str
    verb_section: str
    definition: str = ""


WIKTIONARY_API_URL = "https://en.wiktionary.org/w/api.php"
WORD_SUGGESTION_API_URL = "https://api.datamuse.com/words?sp={query}*&md=p&max={limit}"
HTTP_TIMEOUT_SECONDS = 8
WIKTIONARY_CACHE: dict[str, WiktionaryVerbEntry | None] = {}
SUGGESTION_CACHE: dict[str, list[str]] = {}


def fetch_json(url: str, attempts: int = 2) -> object | None:
    request = Request(url, headers={"User-Agent": "verbIndenter/1.0"})

    for _attempt in range(attempts):
        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            continue

    return None


def fetch_wiktionary_wikitext(word: str) -> str | None:
    params = urlencode(
        {
            "action": "query",
            "prop": "revisions",
            "titles": word,
            "rvslots": "main",
            "rvprop": "content",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        }
    )
    data = fetch_json(f"{WIKTIONARY_API_URL}?{params}")

    if not isinstance(data, dict):
        return None

    pages = data.get("query", {}).get("pages", [])
    if not isinstance(pages, list) or not pages:
        return None

    page = pages[0]
    if not isinstance(page, dict) or page.get("missing"):
        return None

    revisions = page.get("revisions", [])
    if not isinstance(revisions, list) or not revisions:
        return None

    slots = revisions[0].get("slots", {})
    if not isinstance(slots, dict):
        return None

    main_slot = slots.get("main", {})
    if not isinstance(main_slot, dict):
        return None

    content = main_slot.get("content")
    return content if isinstance(content, str) else None


def lookup_wiktionary_verb(word: str) -> WiktionaryVerbEntry | None:
    normalized_word = normalize_word(word)
    if not normalized_word:
        return None

    if normalized_word in WIKTIONARY_CACHE:
        return WIKTIONARY_CACHE[normalized_word]

    wikitext = fetch_wiktionary_wikitext(normalized_word)
    if wikitext is None:
        return None

    english_section = extract_language_section(wikitext, "English")
    verb_section = extract_part_of_speech_section(english_section, "Verb")
    if not verb_section:
        WIKTIONARY_CACHE[normalized_word] = None
        return None

    entry = WiktionaryVerbEntry(
        word=normalized_word,
        wikitext=wikitext,
        verb_section=verb_section,
        definition=extract_definition(verb_section),
    )
    WIKTIONARY_CACHE[normalized_word] = entry
    return entry


def normalize_word(word: str) -> str:
    return word.strip().lower()


def extract_language_section(wikitext: str, language: str) -> str:
    pattern = re.compile(rf"^=={re.escape(language)}==\s*$", re.MULTILINE)
    match = pattern.search(wikitext)
    if match is None:
        return ""

    next_language = re.search(r"^==[^=\n]+==\s*$", wikitext[match.end() :], re.MULTILINE)
    if next_language is None:
        return wikitext[match.end() :]

    return wikitext[match.end() : match.end() + next_language.start()]


def extract_part_of_speech_section(language_section: str, part_of_speech: str) -> str:
    if not language_section:
        return ""

    pattern = re.compile(rf"^(={{3,6}}){re.escape(part_of_speech)}\1\s*$", re.MULTILINE)
    match = pattern.search(language_section)
    if match is None:
        return ""

    heading_level = len(match.group(1))
    rest = language_section[match.end() :]
    next_heading_pattern = re.compile(r"^(={3,6})[^=\n]+?\1\s*$", re.MULTILINE)

    for next_heading in next_heading_pattern.finditer(rest):
        if len(next_heading.group(1)) <= heading_level:
            return rest[: next_heading.start()]

    return rest


def extract_definition(verb_section: str) -> str:
    for line in verb_section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("# "):
            continue
        if stripped.startswith("# {{"):
            continue

        return clean_wikitext(stripped[2:])

    return ""


def clean_wikitext(text: str) -> str:
    text = re.sub(r"\{\{lb\|en\|([^}]+)\}\}", r"(\1)", text)
    text = re.sub(r"\{\{gloss\|([^}]+)\}\}", r"(\1)", text)
    text = re.sub(r"\{\{[^}|]+\|([^}|]+)\}\}", r"\1", text)
    text = re.sub(r"\{\{[^}]+\}\}", "", text)
    text = re.sub(r"\[\[([^]|]+)\|([^]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^]]+)\]\]", r"\1", text)
    text = re.sub(r"'{2,}", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_template(section: str, template_name: str) -> list[str] | None:
    match = re.search(r"\{\{" + re.escape(template_name) + r"((?:[^{}]|\{(?!\{)|\}(?!\}))*)\}\}", section)
    if match is None:
        return None

    raw_parts = match.group(1).lstrip("|").split("|")
    return [part.strip() for part in raw_parts if part.strip()]


def verb_from_wiktionary_word(word: str) -> Verb | None:
    entry = lookup_wiktionary_verb(word)
    if entry is None:
        return None

    lemma = extract_lemma_from_form_section(entry.verb_section)
    if lemma and lemma != entry.word:
        return verb_from_wiktionary_word(lemma)

    forms = extract_en_verb_forms(entry.word, entry.verb_section)
    if forms is None:
        return None

    simple_past, participle = forms
    kind = "regular" if simple_past == regular_past_form(entry.word) and participle == simple_past else "irregular"
    return Verb(entry.word, simple_past, participle, kind, entry.definition, "Wiktionary")


def extract_lemma_from_form_section(verb_section: str) -> str | None:
    patterns = (
        r"\{\{en-past of\|([^}|]+)",
        r"\{\{en-simple past of\|([^}|]+)",
        r"\{\{past participle of\|en\|([^}|]+)",
        r"\{\{en-past participle of\|([^}|]+)",
        r"\{\{inflection of\|en\|([^}|]+)\|\|[^}]*\bpast\b",
    )

    for pattern in patterns:
        match = re.search(pattern, verb_section)
        if match:
            return normalize_word(match.group(1))

    text_match = re.search(r"simple past(?: tense)?(?: and past participle)? of \[\[([^]|]+)", verb_section)
    if text_match:
        return normalize_word(text_match.group(1))

    return None


def extract_en_verb_forms(word: str, verb_section: str) -> tuple[str, str] | None:
    template = extract_template(verb_section, "en-verb")
    if template is None:
        return None

    positional = [part for part in template if "=" not in part]
    named = dict(part.split("=", 1) for part in template if "=" in part)

    angle_forms = extract_angle_forms(word, positional)
    if angle_forms is not None:
        return angle_forms

    if named.get("past") and named.get("past2"):
        past = join_forms(named["past"], named["past2"])
    elif named.get("past"):
        past = named["past"]
    elif len(positional) >= 3:
        past = positional[2]
    else:
        past = regular_past_form(word)

    if named.get("past participle") and named.get("past participle2"):
        participle = join_forms(named["past participle"], named["past participle2"])
    elif named.get("past participle"):
        participle = named["past participle"]
    elif len(positional) >= 4:
        participle = positional[3]
    elif len(positional) >= 3:
        participle = positional[2]
    else:
        participle = past

    return clean_form(past, word), clean_form(participle, word)


def extract_angle_forms(word: str, positional: list[str]) -> tuple[str, str] | None:
    if len(positional) != 1:
        return None

    match = re.search(r"<([^>]*)>", positional[0])
    if match is None:
        return None

    parts = match.group(1).split(",")
    if len(parts) < 4:
        return None

    past = clean_form(parts[2], word)
    participle = clean_form(parts[3], word)
    return past, participle


def resolve_template_form(word: str, value: str) -> str:
    if value == "d":
        return f"{word}d"
    if value == "ed":
        return f"{word}ed"
    if value == "es":
        return f"{word}es"
    if value == "ies":
        return f"{word[:-1]}ied"
    if value == "+":
        return regular_past_form(word)
    return value


def clean_form(value: str, word: str = "") -> str:
    value = re.sub(r"<[^>]+>", "", value)
    alternatives = split_form_alternatives(value)
    cleaned = []

    for alternative in alternatives:
        alternative = resolve_template_form(word, alternative.strip())
        alternative = re.sub(r"\[[^]]+\]", "", alternative)
        alternative = clean_wikitext(alternative)
        if alternative and alternative not in cleaned:
            cleaned.append(alternative)

    return "/".join(cleaned)


def split_form_alternatives(value: str) -> list[str]:
    parts = re.split(r"[,;:]", value)
    return [part for part in parts if part.strip()]


def join_forms(*forms: str) -> str:
    cleaned_forms = [clean_form(form) for form in forms if clean_form(form)]
    return "/".join(cleaned_forms)


def regular_past_form(verb: str) -> str:
    if verb.endswith("e"):
        return f"{verb}d"
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        return f"{verb[:-1]}ied"
    return f"{verb}ed"


def fetch_online_suggestions(query: str, limit: int = 5) -> list[str]:
    normalized_query = normalize_word(query)
    if len(normalized_query) < 2:
        return []

    if normalized_query in SUGGESTION_CACHE:
        return SUGGESTION_CACHE[normalized_query][:limit]

    url = WORD_SUGGESTION_API_URL.format(query=quote(normalized_query), limit=limit * 5)
    data = fetch_json(url)
    suggestions = parse_word_suggestions(data)
    SUGGESTION_CACHE[normalized_query] = suggestions
    return suggestions[:limit]


def parse_word_suggestions(data: object | None) -> list[str]:
    if not isinstance(data, list):
        return []

    suggestions: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue

        word = item.get("word")
        tags = item.get("tags", [])
        if not isinstance(word, str) or not isinstance(tags, list):
            continue
        if "v" not in tags or not word.isalpha():
            continue

        suggestions.append(word.lower())

    return suggestions


def suggest(query: str, limit: int = 5, use_online: bool = True) -> list[Verb]:
    normalized_query = normalize_word(query)
    if not normalized_query or not use_online:
        return []

    result: list[Verb] = []

    exact = verb_from_wiktionary_word(normalized_query)
    if exact is not None:
        result.append(exact)

    for word in fetch_online_suggestions(normalized_query, limit):
        verb = verb_from_wiktionary_word(word)
        if verb is None or verb in result:
            continue

        result.append(verb)
        if len(result) == limit:
            break

    return result[:limit]
