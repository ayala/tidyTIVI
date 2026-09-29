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

    def test_notifications_are_private_and_update_one_persistent_item(self):
        import sys
        import types
        from unittest.mock import MagicMock
        model=MagicMock();notification=MagicMock()
        notification.pk=42;notification.notification_key='tidytivi-export'
        model.objects.update_or_create.return_value=(notification,False)
        sender=MagicMock()
        with patch.dict(sys.modules,{'core.models':types.SimpleNamespace(SystemNotification=model), 'core.utils':types.SimpleNamespace(send_websocket_notification=sender)}):
            b.announce({'state':'running','message':'Building backup'})
            options=model.objects.update_or_create.call_args.kwargs
            self.assertEqual(options['notification_key'],'tidytivi-export')
            self.assertTrue(options['defaults']['admin_only'])
            self.assertEqual(options['defaults']['priority'],'high')
            self.assertFalse(sender.call_args.args[0]['is_dismissed'])
            b.announce({'state':'failed','message':'Upload failed'})
            self.assertEqual(model.objects.update_or_create.call_args.kwargs['defaults']['notification_type'],'warning')

    def test_notification_failure_does_not_fail_export(self):
        import sys,types
        from unittest.mock import MagicMock
        model=MagicMock();model.objects.update_or_create.side_effect=RuntimeError('Unavailable')
        with patch.dict(sys.modules,{'core.models':types.SimpleNamespace(SystemNotification=model),'core.utils':types.SimpleNamespace(send_websocket_notification=MagicMock())}):
            b.announce({'state':'running','message':'Building'})
