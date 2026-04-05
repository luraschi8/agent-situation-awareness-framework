"""Intent router — maps a message to a list of relevant memory domains.

Matching strategy: each keyword matches at a word boundary, optionally
followed by a common English suffix (s, es, ed, ing). This catches the
most common plurals and verb forms without resorting to NLP lemmatization.

Examples:
  keyword "meeting" matches: meeting, meetings, meetinged (n/a), meetinging (n/a)
  keyword "deploy"  matches: deploy, deploys, deployed, deploying
  keyword "home"    matches: home, homes  — but NOT homework or homepage
  keyword "report"  matches: report, reports, reported, reporting
                   — but NOT reportedly or reportage

Known limitations (the regex is a pragmatic tradeoff, not an NLP stack):
  - Does not catch irregular plurals (child/children, man/men)
  - Does not catch -ment, -tion, -er, -ly, -able and similar suffixes
  - Does not catch verb tense changes (go/went, run/ran)
  - Does not catch synonyms — users must curate keyword lists

If a specific miss matters for your use case, add the variant directly
to your router-config.json. For broader coverage, a future enhancement
could add a lemmatization option behind a config flag.
"""

import json
import os
import re

from skills.saf_core.lib.domains import CONFIG_PATH, DEFAULT_KEYWORDS

GENERAL_DOMAIN = "general"

# Common English suffixes that the router will match automatically.
# Order matters for regex alternation: longer suffixes first so that
# "es" is preferred over "s" where applicable.
COMMON_SUFFIXES = ("ing", "ed", "es", "s")
_SUFFIX_PATTERN = "(?:" + "|".join(COMMON_SUFFIXES) + ")?"


def load_domain_keywords():
    """Loads domain keywords from config file, falling back to defaults."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return DEFAULT_KEYWORDS


def _word_match(keyword, text):
    """Matches keyword as a whole word, plus common English suffixes.

    Pattern: \\b<keyword>(ing|ed|es|s)?\\b

    The trailing \\b prevents keyword "home" from matching "homework"
    (word character follows) while still allowing "homes" (matched via
    the optional suffix group, followed by \\b).
    """
    pattern = r'\b' + re.escape(keyword) + _SUFFIX_PATTERN + r'\b'
    return bool(re.search(pattern, text))


def get_relevant_domains(message, domain_keywords=None):
    """Determines which memory domains to inject based on message intent."""
    if domain_keywords is None:
        domain_keywords = load_domain_keywords()
    msg = message.lower()
    domains = [
        domain
        for domain, keywords in domain_keywords.items()
        if any(_word_match(k, msg) for k in keywords)
    ]
    return domains if domains else [GENERAL_DOMAIN]
