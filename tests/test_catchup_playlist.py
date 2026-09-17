import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tidyTIVI.exporter import m3u

class CatchupPlaylistTests(unittest.TestCase):
    def test_only_archive_channels_advertise_provider_retention(self):
        channels=[{'id':1,'provider_url':'https://example.test/live/u/p/7.ts','group_name':'News','catchup_hours':72},
                  {'id':2,'provider_url':'https://example.test/live/u/p/8.ts','group_name':'News','catchup_hours':0}]
        playlist=m3u({'profiles':[{'name':'Example','channels':channels}]}).decode().splitlines()
        self.assertIn('catchup="xc" catchup-days="3"',playlist[1])
        self.assertNotIn('catchup=',playlist[3])
        self.assertEqual(playlist[2],channels[0]['provider_url'])
