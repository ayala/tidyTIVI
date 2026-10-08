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

    def test_xc_preferred_over_m3u_and_custom(self):
        direct=N(stream=N(pk=1,m3u_account=None))
        m3u=link(2,8);m3u.stream.m3u_account.account_type='M3U'
        xc=link(3,9)
        self.assertEqual(select_stream([direct,m3u,xc],{'account_8':True,'account_9':True}).pk,3)
        self.assertEqual(select_stream([m3u,xc],{'account_8':True}).pk,2)
        self.assertIsNone(select_stream([m3u,xc],{}))
        self.assertEqual(select_stream([direct],{}).pk,1)
        self.assertIsNone(select_stream([direct],{'include_direct_streams':False}))

    def test_explicit_xc_priority_precedes_assignment_order(self):
        self.assertEqual(select_stream([link(1,8),link(2,9)],{'account_8':True,'account_9':True,'priority_8':'20','priority_9':'1'}).pk,2)

    def test_remote_direct_url_validation(self):
        from plugin import direct_stream_problem
        for url in ['http://127.0.0.1/live','http://192.168.1.2/live','http://[::1]/live','http://dispatcharr.local/live','file:///live']:
            self.assertIsNotNone(direct_stream_problem(url))
        self.assertIsNone(direct_stream_problem('https://fast.example/live.m3u8'))

    def test_valid_direct_fallback_skips_private_first_url(self):
        private=N(stream=N(pk=1,m3u_account=None,url='http://192.168.1.2/live'))
        public=N(stream=N(pk=2,m3u_account=None,url='https://fast.example/live.m3u8'))
        self.assertEqual(select_stream([private,public],{}).pk,2)
