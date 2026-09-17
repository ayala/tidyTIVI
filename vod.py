"""Snapshot current Dispatcharr VOD curation for native TiviMate XC VOD."""
import json
import math
from urllib.parse import quote


def collect_vod(settings, accounts):
    from django.db.models import F
    from apps.m3u.models import M3UAccount
    from apps.vod.models import M3UMovieRelation,M3USeriesRelation,M3UVODCategoryRelation
    result={'movies':[],'series':[]}
    for account in M3UAccount.objects.filter(account_type='XC',is_active=True).order_by('pk'):
        if str(settings.get(f'account_{account.pk}',False)).lower() not in ('true','1','yes','on'):continue
        categories={r.category_id:r for r in M3UVODCategoryRelation.objects.filter(m3u_account=account).select_related('category')}
        added=False
        for kind,model,field in [('movies',M3UMovieRelation,'movie'),('series',M3USeriesRelation,'series')]:
            fields=['id','category_id','category__name',field+'__name',field+'__rating',field+'__logo__url', 'stream_id' if kind=='movies' else 'external_series_id']
            if kind=='movies':fields.append('container_extension')
            query=model.objects.filter(m3u_account=account).select_related('category',field+'__logo').only(*fields).annotate(tidytivi_marker=F('custom_properties__vodarranger')).order_by('pk')
            for relation in query.iterator(chunk_size=2000):
                marker=relation.tidytivi_marker or {}
                # A renamed/combined target may have no provider category relation;
                # use tidyVOD's original-category marker to honor its enabled state.
                origin=marker.get('original_category_id') or relation.category_id
                category=categories.get(origin) or categories.get(relation.category_id)
                if category is None or not category.enabled or (category.custom_properties or {}).get('vodarranger',{}).get('hidden_category'):continue
                item=getattr(relation,field)
                external=relation.stream_id if kind=='movies' else relation.external_series_id
                try:external=int(external)
                except (ValueError,TypeError):continue
                try:rating=float(item.rating);rating=rating if math.isfinite(rating) else None
                except (ValueError,TypeError):rating=None
                result[kind].append({'id':relation.pk,'account_id':account.pk,'xc_id':external,
                    'name':item.name,'category':relation.category.name if relation.category else 'Uncategorized',
                    'category_id':relation.category_id,'image':item.logo.url if item.logo else '',
                    'rating':rating,'extension':(relation.container_extension or 'mp4') if kind=='movies' else None})
                added=True
        if added:accounts[account.pk]={'id':account.pk,'name':account.name,'server_url':account.server_url,'username':account.username,'password':account.password}
    return result


def add_vod(db,job,playlist_template,insert):
    vod=job.get('vod') or {'movies':[],'series':[]}
    result={'movies':len(vod['movies']),'series':len(vod['series']),'playlists':0}
    accounts={a['id']:a for a in job['accounts']}
    for aid in sorted({x['account_id'] for kind in vod.values() for x in kind}):
        account=accounts[aid];movies=[x for x in vod['movies'] if x['account_id']==aid];series=[x for x in vod['series'] if x['account_id']==aid]
        values={k:v for k,v in playlist_template.items() if k!='id'}
        import time
        values.update(name=account['name']+' · VOD',url='xc:'+json.dumps({'h':account['server_url'].rstrip('/'),'u':account['username'],'p':account['password'],'o':'ts'},separators=(',',':')),
            include_tv_channels=0,include_vod=1,is_vod=1,is_enabled=1,auto_update=0,last_update_time=int(time.time()*1000),
            channel_count=0,movie_count=len(movies),series_count=len(series),tvg_urls='',position=sum(bool(p['channels']) for p in job['profiles'])+result['playlists'] if job['settings'].get('profile_playlists',True) else 1+result['playlists'],
            is_visible_in_all_channels=0,is_visible_in_all_favorites=0,are_new_groups_visible=0,
            are_new_movie_groups_visible=0,are_new_series_groups_visible=0,expiration_date=None,max_connections=None)
        pid=insert(db,'playlists',values);result['playlists']+=1
        for kind,items in [('movies',movies),('series',series)]:
            groups={}
            table='movie_categories' if kind=='movies' else 'series_categories'
            for position,item in enumerate(items):
                key=item['category']
                if key not in groups:
                    groups[key]=insert(db,table,{'playlist_id':pid,'name':key,'is_visible':1,'position_in_playlist':len(groups),'manual_position':len(groups),'item_count':0})
                values={'playlist_id':pid,'category_id':groups[key],'xc_id':item['xc_id'],'name':item['name'],
                    'image':item['image'],'rating':item['rating'],'position_in_category':position,'display_mode':1,
                    'is_favorite':0,'last_turn_on_time':0,'deleted_time':None}
                if kind=='movies':
                    ext=item['extension']
                    if not ext.isalnum():raise ValueError('Unsupported movie extension.')
                    values.update(url=account['server_url'].rstrip('/')+'/movie/'+quote(account['username'],safe='')+'/'+quote(account['password'],safe='')+'/'+str(item['xc_id'])+'.'+ext,
                        added_time=0,last_played_position_ms=0,duration_ms=0)
                else:values.update(last_modified_time=0,last_episode_xc_id=None)
                insert(db,kind,values)
            for gid in groups.values():db.execute('UPDATE '+table+' SET item_count=(SELECT count(*) FROM '+kind+' WHERE category_id=?) WHERE id=?',(gid,gid))
    return result
