import os
import re
import time
from datetime import datetime, timedelta
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import polars as pl

auth_manager = SpotifyClientCredentials(
    client_id=os.getenv('SPOTIPY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIPY_CLIENT_SECRET')
)
sp = spotipy.Spotify(auth_manager=auth_manager)

def search_curators(keywords, limit=50):
    curator_list = []
    seen_ids = set()
    # 30日だと厳しすぎるので 90日（約3ヶ月）に拡大
    active_period = datetime.now() - timedelta(days=90)

    for kw in keywords:
        print(f"--- Searching: {kw} ---")
        try:
            results = sp.search(q=kw, type='playlist', limit=limit)
            items = results['playlists']['items']
            print(f"Found {len(items)} raw results for '{kw}'")
            
            for playlist in items:
                if not playlist or playlist['id'] in seen_ids: continue
                
                try:
                    tracks = sp.playlist_tracks(playlist['id'], limit=1)
                    if not tracks['items'] or tracks['items'][0]['added_at'] is None: continue
                    
                    last_added = datetime.strptime(tracks['items'][0]['added_at'], '%Y-%m-%dT%H:%M:%SZ')
                    
                    if last_added > active_period:
                        desc = playlist['description'] or ""
                        sns_match = re.findall(r'@([\\\\w\\\\.]+)|ig:\\\\s*([\\\\w\\\\.]+)|twitter:\\\\s*([\\\\w\\\\.]+)', desc, re.IGNORECASE)
                        sns_handles = [item for sublist in sns_match for item in sublist if item]
                        
                        curator_list.append({
                            'name': playlist['name'],
                            'owner': playlist['owner']['display_name'],
                            'last_updated': last_added.strftime('%Y-%m-%d'),
                            'sns': ", ".join(list(set(sns_handles))),
                            'url': playlist['external_urls']['spotify'],
                            'description': desc[:100]
                        })
                        seen_ids.add(playlist['id'])
                except: continue
                time.sleep(0.1)
        except Exception as e:
            print(f"Search Error: {e}")
            continue
    return pl.DataFrame(curator_list)

if __name__ == "__main__":
    # キーワードをより広く、強力に設定
    target_keywords = [
        '叙情系', 'Lyrical Hardcore', 'Melodic Hardcore Japan', 
        'Japanese Hardcore', 'Emotional Hardcore', 'Screamo Japan',
        'envy band', 'waterweed', 'Crystal Lake fans' # 関連バンド名を入れるのがコツ
    ]
    df = search_curators(target_keywords)
    if not df.is_empty():
        df.write_csv("curator_list.csv")
        print(f"--- SUCCESS: Found {len(df)} active playlists! ---")
    else:
        print("--- NO RESULTS FOUND. Try broader keywords. ---")