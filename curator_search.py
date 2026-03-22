import os
import re
import time
from datetime import datetime, timedelta
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import polars as pl

# 認証設定
auth_manager = SpotifyClientCredentials(
    client_id=os.getenv('SPOTIPY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIPY_CLIENT_SECRET')
)
sp = spotipy.Spotify(auth_manager=auth_manager)

def search_curators(keywords, limit=50):
    curator_list = []
    seen_ids = set()
    one_month_ago = datetime.now() - timedelta(days=30)

    for kw in keywords:
        print(f"Searching: {kw}...")
        try:
            results = sp.search(q=kw, type='playlist', limit=limit)
            if not results['playlists']['items']: continue
            
            for playlist in results['playlists']['items']:
                if not playlist or playlist['id'] in seen_ids: continue
                
                try:
                    tracks = sp.playlist_tracks(playlist['id'], limit=1)
                    if not tracks['items'] or tracks['items'][0]['added_at'] is None: continue
                    
                    last_added = datetime.strptime(tracks['items'][0]['added_at'], '%Y-%m-%dT%H:%M:%SZ')
                    
                    if last_added > one_month_ago:
                        desc = playlist['description'] or ""
                        sns_match = re.findall(r'@([\\w\\.]+)|ig:\\s*([\\w\\.]+)|twitter:\\s*([\\w\\.]+)', desc, re.IGNORECASE)
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
    target_keywords = ['叙情系', 'Lyrical Hardcore', 'Osaka Hardcore', 'Melodic Hardcore Japan']
    df = search_curators(target_keywords)
    if not df.is_empty():
        df.write_csv("curator_list.csv")
        print(f"Successfully found {len(df)} active playlists.")
    else:
        print("No active playlists found.")
