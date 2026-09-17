import unittest
from types import SimpleNamespace as N
from plugin import select_stream


def link(stream_id, account_id):
    return N(stream=N(pk=stream_id, m3u_account=N(pk=account_id)))


class ProviderSelectionTests(unittest.TestCase):
    def test_only_explicitly_selected_accounts_are_used(self):
        self.assertIsNone(select_stream([link(10, 2), link(11, 3)], {}))
        self.assertEqual(select_stream([link(10, 2), link(11, 3)], {'account_3':True}).pk,11)

    def test_filter_uses_first_assigned_alternative(self):
        self.assertEqual(select_stream([link(10, 2), link(11, 3), link(12, 3)],
                                      {'account_2': False, 'account_3': True}).pk, 11)

    def test_missing_provider_does_not_use_excluded_stream(self):
        self.assertIsNone(select_stream([link(10, 2)], {'account_2': False}))

    def test_saved_string_false(self):
        self.assertEqual(select_stream([link(10, 2), link(11, 3)],
                                      {'account_2': 'false', 'account_3': 'true'}).pk, 11)

    def test_no_assignments(self):
        self.assertIsNone(select_stream([], {}))

    def test_stale_first_choice_is_skipped(self):
        stale = link(10, 3)
        stale.stream.is_stale = True
        self.assertEqual(select_stream([stale, link(11, 3)], {'account_3':True}).pk, 11)

    def test_only_stale_assignments_are_excluded(self):
        stale = link(10, 3)
        stale.stream.is_stale = True
        self.assertIsNone(select_stream([stale], {}))
