import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import background_export as b

class BackgroundExportTests(unittest.TestCase):
    def test_private_atomic_state_and_interrupted_job(self):
        with tempfile.TemporaryDirectory() as root:
            settings={'export_directory':root}
            directory=b.state_directory(settings)
            b.write(directory/'status.json',{'state':'running','pid':99999999,'message':'working'})
            self.assertEqual((directory/'status.json').stat().st_mode & 0o777,0o600)
            self.assertEqual(b.status(settings)['export_status'],'failed')
            self.assertIn('interrupted',b.status(settings)['message'])

    def test_status_does_not_expose_private_result(self):
        with tempfile.TemporaryDirectory() as root:
            settings={'export_directory':root};directory=b.state_directory(settings)
            b.write(directory/'status.json',{'state':'complete','message':'Done','pid':123})
            b.write(directory/'result.json',{'secret':'private-secret'})
            self.assertEqual(b.status(settings),{'status':'ok','export_status':'complete','message':'Done'})

    def test_export_returns_without_building_catalogue(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
        from tidyTIVI.plugin import Plugin
        with patch('tidyTIVI.background_export.start',return_value={'status':'ok','message':'started'}) as start, patch('tidyTIVI.plugin.build_job') as build:
            result=object.__new__(Plugin).run('export_backups',{}, {'settings':{'test':True}})
            self.assertEqual(result['message'],'started');start.assert_called_once_with({'test':True});build.assert_not_called()
