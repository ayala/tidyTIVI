"""Detached exports with private state and cross-process duplicate protection."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone


def announce(state):
    """Use Dispatcharr's supported notification API; failures never stop exports."""
    try:
        from core.models import SystemNotification
        from core.utils import send_websocket_notification
        title = {'running': 'tidyTIVI · Export in progress',
                 'complete': 'tidyTIVI · Export complete',
                 'failed': 'tidyTIVI · Export failed'}[state['state']]
        notification, _ = SystemNotification.objects.update_or_create(
            notification_key='tidytivi-export', defaults={
                'title': title, 'message': state['message'],
                'notification_type': 'warning' if state['state'] == 'failed' else 'info',
                'priority': 'high', 'admin_only': True, 'is_active': True,
                'expires_at': None, 'action_data': {}})
        notification.dismissals.all().delete()
        send_websocket_notification({
            'id': notification.pk, 'notification_key': notification.notification_key,
            'title': notification.title, 'message': notification.message,
            'notification_type': notification.notification_type,
            'priority': notification.priority, 'admin_only': True,
            'is_active': True, 'is_dismissed': False, 'action_data': {},
            'created_at': notification.created_at.isoformat()})
    except Exception:
        import logging
        logging.getLogger(__name__).warning('tidyTIVI export notification could not be delivered; status remains available.')


def write(path, value):
    temporary = path.with_suffix('.tmp')
    with open(temporary, 'w', opener=lambda p, flags: os.open(p, flags, 0o600)) as handle:
        json.dump(value, handle)
    os.replace(temporary, path)


def state_directory(settings):
    directory = Path(settings.get('export_directory') or '/data/exports/tidytivi') / '.export-task'
    if not directory.is_absolute():
        raise ValueError('Export directory must be an absolute path.')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory


def alive(state):
    try:
        pid = int(state.get('pid', 0))
        if pid <= 0: return False
        os.kill(pid, 0)
        proc = Path('/proc') / str(pid) / 'cmdline'
        return not proc.exists() or b'background_export.py' in proc.read_bytes()
    except (OSError, ValueError):
        return False


def read(directory):
    path = directory / 'status.json'
    state = json.loads(path.read_text()) if path.exists() else {'state': 'idle', 'message': 'No background export has been started.'}
    if state['state'] == 'running' and not alive(state):
        state.update(state='failed', message='Export was interrupted. Start Export bundle again.')
    return state


def status(settings):
    state = read(state_directory(settings))
    return {'status': 'ok', 'export_status': state['state'], 'message': state['message']}


def start(settings):
    from django.conf import settings as django_settings
    directory = state_directory(settings)
    with open(directory / 'start.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = read(directory)
        if state['state'] == 'running':
            return {'status': 'ok', 'message': 'An export is already running. Progress and completion appear automatically in Dispatcharr notifications.'}
        request = {'settings': settings, 'django_settings': django_settings.SETTINGS_MODULE,
                   'project_root': str(django_settings.BASE_DIR)}
        write(directory / 'request.json', request)
        try:
            process = subprocess.Popen([shutil.which('python3') or sys.executable,
                str(Path(__file__).resolve()), str(directory)], cwd=request['project_root'],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True, close_fds=True)
        except OSError:
            (directory / 'request.json').unlink(missing_ok=True)
            raise ValueError('Could not start the background export process.') from None
        write(directory / 'status.json', {'state': 'running', 'pid': process.pid,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'message': 'Export running: loading the complete XC catalog. Progress and completion appear automatically in Dispatcharr notifications.'})
    return {'status': 'ok', 'message': 'Export started in the background. You can close this page. Progress and completion appear automatically in Dispatcharr notifications.'}


def run(directory):
    with open(directory / 'start.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads((directory / 'status.json').read_text())
        request = json.loads((directory / 'request.json').read_text())
        (directory / 'request.json').unlink()
    def progress(message):
        state['message'] = message
        write(directory / 'status.json', state)
        announce(state)
    try:
        os.environ['DJANGO_SETTINGS_MODULE'] = request['django_settings']
        sys.path.insert(0, request['project_root'])
        import django
        django.setup()
        announce(state)
        import importlib.util
        package = Path(__file__).resolve().parent
        spec = importlib.util.spec_from_file_location('_tidytivi_worker', package / '__init__.py', submodule_search_locations=[str(package)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        from _tidytivi_worker.plugin import Plugin
        result = Plugin().run('export_backups', {}, {'settings': request['settings'], 'progress': progress}, _background=True)
        write(directory / 'result.json', result)
        if result['status'] != 'ok':
            state.update(state='failed', message=result['message'])
        else:
            report = json.loads(result['message'])
            cloud = report.get('cloud')
            counts = report.get('vod', {})
            message = f"Export complete: {counts.get('movies', 0):,} movies and {counts.get('series', 0):,} series. "
            if cloud and cloud.get('status') == 'ok':
                message += 'Dropbox updated. Run Update TiviMate in the companion.'
            elif cloud:
                message += 'Local bundle saved, but Dropbox upload failed: ' + cloud.get('message', 'Check the Dropbox connection.')
            else:
                message += 'Local bundle saved. Automatic cloud upload is disabled.'
            state.update(state='failed' if cloud and cloud.get('status') != 'ok' else 'complete', message=message)
    except Exception:
        state.update(state='failed', message='Background export failed. Check server availability and retry. Your previous cloud bundle remains available.')
    state['finished_at'] = datetime.now(timezone.utc).isoformat()
    write(directory / 'status.json', state)
    announce(state)


if __name__ == '__main__':
    run(Path(sys.argv[1]))
