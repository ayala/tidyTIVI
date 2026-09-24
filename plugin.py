"""Read-only Dispatcharr export of selected profiles for one combined native TiviMate backup."""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def enabled(value):
    return value is True or str(value).lower() in ('1', 'true', 'yes', 'on')


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.tidytivi-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def select_stream(links, settings):
    """Respect assigned priority within the explicitly selected providers."""
    return next((link.stream for link in links
                 if not getattr(link.stream, 'is_stale', False) and link.stream.m3u_account and
                 enabled(settings.get(f'account_{link.stream.m3u_account.pk}', False))), None)


def build_job(settings):
    from apps.channels.models import ChannelProfile, ChannelProfileMembership, ChannelStream
    from django.db.models import Prefetch

    profiles = [p for p in ChannelProfile.objects.order_by('name')
                if enabled(settings.get(f'profile_{p.pk}', False))]
    if not profiles:
        raise ValueError('Select at least one profile and save the settings first.')
    job = {'schema': 'tidytivi.job.v1', 'id': uuid4().hex,
           'created_at': datetime.now(timezone.utc).isoformat(),
           'target_version': '5.3.3', 'profiles': [], 'accounts': [], 'epg_sources': [],
           'settings': {'names': enabled(settings.get('names', True)),
                        'logos': enabled(settings.get('logos', True)),
                        'epg': enabled(settings.get('epg', True)),
                        'number_prefix': enabled(settings.get('number_prefix', False)),
                        'profile_playlists': enabled(settings.get('profile_playlists', True)),
                        'playlist_name': str(settings.get('playlist_name') or 'tidyTIVI'),
                        'include_subgroups': enabled(settings.get('include_subgroups', True)),
                        'uppercase_groups': enabled(settings.get('uppercase_groups', False)),
                        'provider_vod': enabled(settings.get('vod', True))},
           'warnings': []}
    from .accounts import catchup_hours
    accounts, sources = {}, {}
    fallback_count = 0
    for profile in profiles:
        rows = ChannelProfileMembership.objects.filter(channel_profile=profile, enabled=True).select_related(
            'channel__logo', 'channel__channel_group', 'channel__epg_data__epg_source').prefetch_related(
            Prefetch('channel__channelstream_set', queryset=ChannelStream.objects.select_related(
                'stream__m3u_account').order_by('order', 'pk'), to_attr='tivi_streams'))
        channels, excluded, reassigned = [], [], []
        for membership in rows:
            ch = membership.channel
            if ch.hidden_from_output:
                continue
            links = ch.tivi_streams
            stream = select_stream(links, settings)
            if stream is None:
                excluded.append({'id': ch.pk, 'name': ch.name, 'number': str(ch.channel_number),
                                 'reason': 'No non-stale assigned stream from a selected provider'})
                continue
            if stream.pk != links[0].stream.pk:
                reassigned.append({'id': ch.pk, 'name': ch.name, 'number': str(ch.channel_number)})
            account = stream.m3u_account
            if not account or account.account_type != 'XC' or not stream.stream_id:
                raise ValueError(f'Channel {ch.pk}: selected stream must be an XC stream with a provider ID.')
            accounts[account.pk] = {'id': account.pk, 'name': account.name,
                'server_url': account.server_url, 'username': account.username,
                'password': account.password}
            fallback_count += max(0, len(links) - 1)
            guide = None
            if job['settings']['epg'] and ch.epg_data_id:
                data = ch.epg_data
                source = data.epg_source
                if source.source_type != 'xmltv' or not source.url or not source.is_active:
                    raise ValueError(f'Channel {ch.pk}: assigned EPG needs an active, URL-based XMLTV source.')
                if source.username or source.password:
                    raise ValueError(f'EPG source {source.pk} uses separate authentication; provide a remotely usable feed URL before export.')
                sources[source.pk] = {'id': source.pk, 'name': source.name,
                    'url': source.url, 'priority': source.priority}
                guide = {'source_id': source.pk, 'xmltv_id': data.tvg_id}
            channels.append({'id': ch.pk, 'name': ch.name, 'number': str(ch.channel_number),
                'group_id': ch.channel_group_id, 'group_name': ch.channel_group.name if ch.channel_group else 'Other',
                'logo_url': ch.logo.url if ch.logo and job['settings']['logos'] else None,
                'epg': guide, 'account_id': account.pk, 'xc_id': stream.stream_id,
                'provider_name': stream.name, 'provider_url': stream.url,
                'provider_category_id': (stream.custom_properties or {}).get('category_id'),
                'catchup_hours': catchup_hours(stream.custom_properties or {}),
                'fallback_count': max(0, len(links) - 1)})
        channels.sort(key=lambda c: (float(c['number']), c['id']))
        if not channels:
            job['warnings'].append(f'Profile {profile.name} omitted from live playlists: no usable assigned stream from the selected providers.')
        job['profiles'].append({'id': profile.pk, 'name': profile.name, 'channels': channels,
                                'excluded_channels': excluded, 'reassigned_channels': reassigned})
    if not any(p['channels'] for p in job['profiles']):
        raise ValueError('The selected profiles have no usable assigned streams from the selected providers.')
    from apps.plugins.models import PluginConfig
    logo_config = PluginConfig.objects.filter(name__iexact='tidyCH').first()
    job['logo_repository'] = None
    if logo_config and job['settings']['logos']:
        saved = logo_config.settings or {}
        mappings = {}
        for line in str(saved.get('profile_mappings', '')).splitlines():
            parts = [x.strip() for x in line.split('|')]
            if len(parts) == 3:
                mappings[parts[0].casefold()] = {'country':parts[1].lower(), 'directory':parts[2]}
        job['logo_repository'] = {'repository': saved.get('github_repository', ''),
            'folders': [{'profile': p['name'], **mappings[p['name'].casefold()]}
                        for p in job['profiles'] if p['name'].casefold() in mappings]}
    if job['settings']['provider_vod']:
        from .vod import collect_vod
        job['vod'] = collect_vod(settings, accounts)
    else:
        job['vod'] = {'movies':[], 'series':[]}
    job['accounts'] = list(accounts.values())
    job['epg_sources'] = sorted(sources.values(), key=lambda s: (-s['priority'], s['id']))
    if fallback_count:
        job['warnings'].append(f'{fallback_count} alternate stream assignments are not exported; only the first assigned stream from a selected provider is used.')
    job['warnings'].extend([
        'Native export targets TiviMate 5.3.3 and requires a privately provisioned template and codec seed.',
        'Install the exported logo pack on the receiver. Update all selected profiles together through tidyTIVI; restoring replaces the TiviMate configuration.',
        'VOD is a snapshot of current curation; tidyVOD scanning continues on Dispatcharr. Automatic stream fallback is not included.',
        'Original channel numbers require the optional name prefix; native custom numbering is not verified.'
    ])
    from .accounts import apply_overrides
    return apply_overrides(job, settings)


def summary(job):
    return {'profiles': [{'name': p['name'], 'channels': len(p['channels']),
                          'excluded_channels': p.get('excluded_channels', []),
                          'reassigned_channels': p.get('reassigned_channels', [])} for p in job['profiles']],
            'epg_sources': [s['name'] for s in job['epg_sources']],
            'vod': {k:len(v) for k,v in job.get('vod',{}).items()},
            'accounts': [a['name'] for a in job['accounts']], 'warnings': job['warnings']}


class Plugin:
    def __init__(self):
        from .setup_page import install
        install()
        # Remove the retired v0.5.0 callback when a running worker reloads us.
        try:
            import sys
            api_urls = sys.modules.get('apps.plugins.api_urls')
            if api_urls is None or not hasattr(api_urls, 'urlpatterns'):
                return
            from django.urls import clear_url_caches
            previous = api_urls.urlpatterns
            kept = [p for p in previous if getattr(p, 'name', None) != 'tidytivi-cloud-callback']
            if len(kept) != len(previous):
                previous[:] = kept
                clear_url_caches()
        except ImportError:
            pass

    @property
    def fields(self):
        from .setup_page import install
        install()
        from apps.channels.models import ChannelProfile
        fields = [{'id': f'profile_{p.pk}', 'label': f'Export {p.name}', 'type': 'boolean',
                   'default': False, 'help_text': 'Include enabled, visible channels from this profile.'}
                  for p in ChannelProfile.objects.order_by('name')]
        from apps.channels.models import ChannelStream
        stream_model = ChannelStream._meta.get_field('stream').related_model
        account_model = stream_model._meta.get_field('m3u_account').related_model
        fields.extend({'id': f'account_{a.pk}', 'label': f'Include provider: {a.name}',
                       'type': 'boolean', 'default': False,
                       'help_text': 'Choose the first assigned stream from included providers; report channels with none.'}
                      for a in account_model.objects.filter(account_type='XC').order_by('name'))
        for a in account_model.objects.filter(account_type='XC').order_by('name'):
            fields.extend([
                {'id':f'override_{a.pk}','label':f'Use different export credentials: {a.name}', 'type':'boolean','default':False,
                 'help_text':'Export only. The replacement account must expose the same mapped stream IDs; validated before export.'},
                {'id':f'export_server_{a.pk}','label':f'{a.name} export server (optional)','type':'string','default':'',
                 'help_text':'Leave blank to use the source provider server.'},
                {'id':f'export_username_{a.pk}','label':f'{a.name} export username','type':'string','default':''},
                {'id':f'export_password_{a.pk}','label':f'{a.name} export password','type':'string','input_type':'password','default':''}])
        fields.append({'id':'playlist_name','label':'Combined playlist name','type':'string','default':'tidyTIVI'})
        for key, label, default, help_text in [
            ('profile_playlists', 'One playlist per profile', True, 'Each profile contains its own curated channel categories. All selected profiles still share one backup; mixed providers stay combined within each profile.'),
            ('include_subgroups', 'Include curated subgroups in combined mode', True, 'Add groups such as DirecTV · Sports alongside the full DirecTV, Sky and Movistar Plus groups.'),
            ('vod', 'Export curated VOD', True, 'Include current curated movies and series from enabled categories of the selected providers. New content is included on the next export.'),
            ('uppercase_groups', 'ALL CAPS channel groups', False, 'Uppercase exported live-TV category names. Channel names, profile playlist names and Dispatcharr stay unchanged.'),
            ('names', 'Use curated channel names', True, 'Custom groups and channel ordering are always exported.'),
            ('logos', 'Export assigned logos', True, 'Includes entire tidyCH country folders plus exact assigned channel images for the receiver.'),
            ('epg', 'Use assigned EPG sources', True, 'Only sources referenced by the selected channels are included.'),
            ('number_prefix', 'Prefix channel names with their number', False, 'Reliable visible numbering workaround, for example 296 · Cartoon Network.'),
]:
            fields.append({'id': key, 'label': label, 'type': 'boolean', 'default': default, 'help_text': help_text})
        fields.append({'id': 'export_directory', 'label': 'Private export directory', 'type': 'string',
                       'default': '/data/exports/tidytivi', 'help_text': 'One backup and update bundle contain all selected profiles. Files contain provider credentials.'})
        fields.extend([
            {'id':'codec_seed_path','label':'Private codec seed file','type':'string',
             'default':'/data/tidytivi/codec-seed.json','help_text':'Provisioned once for this installation; no Android worker is required.'},
            {'id':'template_path','label':'Private baseline backup file','type':'string',
             'default':'/data/tidytivi/template.tmb','help_text':'Must match the codec seed. Provides TiviMate 5.3.3 settings and database schema.'}
        ])
        # Preserve legacy authorization before the settings UI can omit hidden fields.
        from apps.plugins.models import PluginConfig
        from .dropbox_upload import migrate_auth, prepare_settings, connection_status
        saved_config = PluginConfig.objects.filter(key='tidytivi').first()
        if saved_config:
            migrate_auth(saved_config.settings or {})
            if (saved_config.settings or {}).get('cloud_provider') == 'drive':
                saved_config.settings = prepare_settings(saved_config.settings)
                saved_config.save(update_fields=['settings'])
        old = (saved_config.settings or {}) if saved_config else {}
        fields.extend([
            {'id':'cloud_upload','label':'Upload after export','type':'boolean','default':enabled(old.get('cloud_upload',old.get('dropbox_upload',False))),
             'help_text':'Update your Dropbox bundle after export. Keep its download link private: the bundle contains exported account credentials.'},
            {'id':'cloud_filename','label':'Bundle filename','type':'string','default':old.get('cloud_filename') or Path(old.get('dropbox_path') or '/tidytivi-latest.zip').name,
             'help_text':'Use a different .zip filename for each recipient. Updates retain the same download link.'},
            {'id':'dropbox_guide','label':'Dropbox setup guide','type':'info',
             'value':'Step-by-step instructions: https://github.com/ayala/tidyTIVI/blob/main/CLOUD-SETUP.md#plugin-users — users do not register an app or configure a tunnel.'},
            {'id':'dropbox_connection','label':'Dropbox connection','type':'info','value':connection_status(old)},
            {'id':'dropbox_auth_code','label':'One-time connection code','type':'string','input_type':'password','default':'',
             'help_text':'Recommended: close Settings and click Docs on the tidyTIVI card. The setup page opens Dropbox and accepts the code directly. This field is only for the legacy Actions workflow.'}

        ])

        return fields

    def run(self, action, params, context):
        settings = context.get('settings', {})
        try:
            if action in ('cloud_connect', 'dropbox_connect', 'dropbox_finish', 'dropbox_cancel'):
                from .dropbox_upload import connect, cancel_connection, authorization_url
                if action == 'dropbox_finish' and 'code' in params:
                    settings = dict(settings, dropbox_auth_code=str(params['code']))
                message = cancel_connection(settings) if action == 'dropbox_cancel' else connect(settings, finish=action == 'dropbox_finish')
                if action in ('cloud_connect', 'dropbox_connect'):
                    url = authorization_url()
                    return {'status':'ok','message':'Click Docs on the tidyTIVI card to open Dropbox setup. Approve access, paste the code there, and finish connecting.','authorization_url':url,'file':url}
                return {'status':'ok','message':message}
            if action in ('cloud_status', 'dropbox_status'):
                from .dropbox_upload import connection_status, authorization_url, read_auth
                auth = read_auth()
                return {'status':'ok','message':connection_status(settings),'connected':bool(auth.get('refresh_token') or auth.get('access_token')),'authorization_url':authorization_url()}
            if action not in ('preview', 'export_job', 'export_backups'):
                return {'status': 'error', 'message': 'Unknown action.'}
            job = build_job(settings)
            report = summary(job)
            if action == 'export_backups':
                from .exporter import export_backups
                report['backups'] = export_backups(job, settings)
                missing=report['backups'][0]['logos'].get('missing_assigned_logos',[])
                if missing:report['warnings'].append(str(len(missing))+' assigned logo URLs could not be downloaded; channels and complete country folders were retained. See missing_assigned_logos.')
                if settings.get('cloud_provider') != 'drive' and enabled(settings.get('cloud_upload',settings.get('dropbox_upload',False))):
                    try:
                        from .dropbox_upload import upload_bundle
                        options=dict(settings)
                        if settings.get('cloud_filename'):
                            name=str(settings['cloud_filename'])
                            if '/' in name or '\\' in name or not name.endswith('.zip'):
                                raise ValueError('Bundle filename must be a .zip filename without folders.')
                            from pathlib import PurePosixPath
                            options['dropbox_path']=str(PurePosixPath(settings.get('dropbox_path') or '/tidytivi-latest.zip').parent/name)
                        report['cloud']=upload_bundle(report['backups'][0]['bundle'],options)
                    except ValueError as exc:
                        report['cloud']={'status':'error','message':str(exc)}
                        report['warnings'].append('Local export succeeded, but cloud publication failed.')
            if action == 'export_job':
                directory = Path(settings.get('export_directory') or '/data/exports/tidytivi')
                if not directory.is_absolute():
                    raise ValueError('Export directory must be an absolute path.')
                destination = directory / (job['id'] + '.job.json')
                atomic_json(destination, job)
                report['job_path'] = str(destination)
            return {'status': 'ok', 'message': json.dumps(report, ensure_ascii=False)}
        except ValueError as exc:
            return {'status': 'error', 'message': str(exc)}
        except Exception:
            # Database/HTTP exceptions can embed credential-bearing URLs.
            return {'status': 'error', 'message': 'Export failed. Verify the provisioned template/codec seed, cryptography dependency, database compatibility, and export-directory permissions.'}
