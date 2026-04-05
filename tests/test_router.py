import json
import os
import tempfile
import unittest
from unittest.mock import patch

from skills.saf_core.lib.domains import DEFAULT_KEYWORDS
from skills.saf_core.lib.router import (
    GENERAL_DOMAIN,
    get_relevant_domains,
    load_domain_keywords,
)


class TestRouterDefaultKeywords(unittest.TestCase):
    """Tests using the built-in default keyword mapping."""

    # --- Single domain matching ---

    def test_work_keywords(self):
        self.assertIn("work", get_relevant_domains("I have a deadline tomorrow"))
        self.assertIn("work", get_relevant_domains("Let's schedule a meeting"))

    def test_family_keywords_with_family_archetype(self):
        # "family" domain only exists in the family archetype, not professional default
        from skills.saf_core.lib.domains import ARCHETYPE_KEYWORDS
        family_kw = ARCHETYPE_KEYWORDS["family"]
        self.assertIn("family", get_relevant_domains("How are the kids doing?", domain_keywords=family_kw))
        self.assertIn("family", get_relevant_domains("Any school events this week?", domain_keywords=family_kw))

    def test_projects_keywords(self):
        self.assertIn("projects", get_relevant_domains("I need to deploy the latest build"))
        self.assertIn("projects", get_relevant_domains("Let's review the coding task"))

    def test_infrastructure_keywords(self):
        self.assertIn("infrastructure", get_relevant_domains("The server is down"))
        self.assertIn("infrastructure", get_relevant_domains("Turn off the lights"))

    # --- Multi-domain matching ---

    def test_multi_domain_work_and_projects(self):
        domains = get_relevant_domains("Deploy the project before the meeting deadline")
        self.assertIn("work", domains)
        self.assertIn("projects", domains)

    def test_multi_domain_projects_and_infrastructure(self):
        domains = get_relevant_domains("Deploy the project to the server")
        self.assertIn("projects", domains)
        self.assertIn("infrastructure", domains)

    # --- Fallback ---

    def test_unrecognized_message_returns_general(self):
        self.assertEqual(get_relevant_domains("Hello there"), [GENERAL_DOMAIN])

    def test_empty_message_returns_general(self):
        self.assertEqual(get_relevant_domains(""), [GENERAL_DOMAIN])

    # --- Edge cases ---

    def test_case_insensitive(self):
        self.assertIn("work", get_relevant_domains("MEETING at 3pm"))
        self.assertIn("infrastructure", get_relevant_domains("The SERVER is down"))

    def test_no_substring_false_positive(self):
        # "home" keyword must NOT match "homework"
        self.assertNotIn("infrastructure", get_relevant_domains("I need to do homework"))
        # "report" keyword must NOT match "reportedly"
        self.assertNotIn("work", get_relevant_domains("She reportedly left early"))
        # "home" must not match "homepage"
        self.assertNotIn("infrastructure", get_relevant_domains("Check the homepage"))

    def test_whole_word_match(self):
        self.assertIn("infrastructure", get_relevant_domains("I'm heading home now"))


class TestRouterSuffixMatching(unittest.TestCase):
    """Tests that the router matches common English suffixes (plurals,
    verb forms) without falling back to lemmatization or introducing
    substring false positives."""

    # --- Plural forms ---

    def test_plural_meeting(self):
        self.assertIn("work", get_relevant_domains("I have several meetings today"))

    def test_plural_deadline(self):
        self.assertIn("work", get_relevant_domains("My deadlines are piling up"))

    def test_plural_home(self):
        self.assertIn("infrastructure", get_relevant_domains("I own two homes"))

    def test_plural_server(self):
        self.assertIn("infrastructure", get_relevant_domains("All our servers are ready"))

    # --- Verb forms (-ed) ---

    def test_past_tense_deploy(self):
        self.assertIn("projects", get_relevant_domains("I deployed the fix"))

    def test_past_tense_report(self):
        self.assertIn("work", get_relevant_domains("She reported the bug"))

    # --- Verb forms (-ing) ---

    def test_present_participle_deploy(self):
        self.assertIn("projects", get_relevant_domains("I am deploying the app"))

    def test_present_participle_code(self):
        self.assertIn("projects", get_relevant_domains("I am coding right now"))

    def test_present_participle_report(self):
        self.assertIn("work", get_relevant_domains("I am reporting the metrics"))

    # --- -es plurals ---

    def test_es_plural_with_custom_keyword(self):
        custom = {"food": ["dish"]}
        self.assertIn("food", get_relevant_domains("I love these dishes", domain_keywords=custom))

    # --- False positives must still be rejected ---

    def test_home_does_not_match_homework(self):
        self.assertNotIn("infrastructure", get_relevant_domains("I need to do homework"))

    def test_home_does_not_match_homepage(self):
        self.assertNotIn("infrastructure", get_relevant_domains("Check the homepage"))

    def test_home_does_not_match_homeowner(self):
        self.assertNotIn("infrastructure", get_relevant_domains("The homeowner called"))

    def test_report_does_not_match_reportedly(self):
        self.assertNotIn("work", get_relevant_domains("She reportedly left early"))

    def test_report_does_not_match_reportage(self):
        self.assertNotIn("work", get_relevant_domains("The reportage was biased"))

    def test_meeting_does_not_match_meetinghouse(self):
        self.assertNotIn("work", get_relevant_domains("The old meetinghouse is closed"))

    def test_gym_does_not_match_gymnasium(self):
        # Note: this relies on "gym" being in the family archetype
        from skills.saf_core.lib.domains import ARCHETYPE_KEYWORDS
        family_kw = ARCHETYPE_KEYWORDS["family"]
        self.assertNotIn("health", get_relevant_domains("The gymnasium is closed", domain_keywords=family_kw))

    def test_deploy_does_not_match_deployment(self):
        # -ment is not in COMMON_SUFFIXES so "deployment" as a noun
        # does not match "deploy" — this is intentional to limit false positives
        self.assertNotIn("projects", get_relevant_domains("The deployment is scheduled"))


class TestRouterCustomKeywords(unittest.TestCase):
    """Tests with user-provided domain keyword configurations."""

    def test_custom_domains_override_defaults(self):
        custom = {"cooking": ["recipe", "dinner", "ingredients"]}
        domains = get_relevant_domains("What's for dinner?", domain_keywords=custom)
        self.assertEqual(domains, ["cooking"])

    def test_custom_domains_fallback_to_general(self):
        custom = {"cooking": ["recipe", "dinner"]}
        self.assertEqual(
            get_relevant_domains("Hello there", domain_keywords=custom),
            [GENERAL_DOMAIN],
        )

    def test_empty_keyword_list_never_matches(self):
        custom = {"placeholder": []}
        self.assertEqual(
            get_relevant_domains("anything at all", domain_keywords=custom),
            [GENERAL_DOMAIN],
        )


class TestRouterConfigLoading(unittest.TestCase):
    """Tests that router loads domain keywords from config file."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmpdir, "router-config.json")

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.tmpdir)

    def test_loads_from_config_file(self):
        config = {"finance": ["budget", "invoice", "tax"]}
        with open(self.config_path, 'w') as f:
            json.dump(config, f)
        with patch("skills.saf_core.lib.router.CONFIG_PATH", self.config_path):
            keywords = load_domain_keywords()
        self.assertEqual(keywords, config)

    def test_falls_back_to_defaults_when_no_config(self):
        with patch("skills.saf_core.lib.router.CONFIG_PATH", self.config_path):
            keywords = load_domain_keywords()
        self.assertEqual(keywords, DEFAULT_KEYWORDS)


if __name__ == '__main__':
    unittest.main()
