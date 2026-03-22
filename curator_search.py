import os
import re
import time
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import polars as pl

# 認証設定
auth_manager = SpotifyClientCredentials(
    client_id=os.getenv('SPOTIPY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIPY_CLIENT_SECRET')
)
sp = spotipy.Spotify(auth_manager=auth_manager)

def search_curators(keywords):
    curator_list = []
    seen_ids = set()

    for kw in keywords:
        print(f"=== Searching for: {kw} ===")
        try:
            # 検索件数を50件に固定
            results = sp.search(q=kw, type='playlist', limit=50)
            items = results['playlists']['items']
            
            for playlist in items:
                if not playlist or playlist['id'] in seen_ids: continue
                
                # プレイリストの基本情報を取得
                desc = playlist['description'] or ""
                owner = playlist['owner']['display_name']
                
                # SNS IDの抽出 (バックスラッシュを修正)
                sns_match = re.findall(r'@([\w\.]+)|ig:\s*([\w\.]+)|twitter:\s*([\w\.]+)', desc, re.IGNORECASE)
                sns_handles = [item for sublist in sns_match for item in sublist if item]
                
                curator_list.append({
                    'name': playlist['name'],
                    'owner': owner,
                    'sns': ", ".join(list(set(sns_handles))),
                    'url': playlist['external_urls']['spotify'],
                    'description': desc[:100]
                })
                seen_ids.add(playlist['id'])
            
            print(f"Current total found: {len(curator_list)}")
            time.sleep(0.2)
        except Exception as e:
            print(f"Error searching {kw}: {e}")
            continue
            
    return pl.DataFrame(curator_list)

if __name__ == "__main__":
    # ヒットしやすい広めのキーワード
    target_keywords = [
        'Japanese Rock 2026', 'Japanese Indie', 'J-Rock New', 
        'Melodic Hardcore', 'Emo Rock', 'Screamo',
        'envy', 'waterweed', 'Crystal Lake', 'PALM'
    ]
    
    df = search_curators(target_keywords)
    
    # 1件もなくても必ずファイルを作成する
    if df.is_empty():
        # ダミーデータを入れてファイル作成を確実にする
        df = pl.DataFrame([{"name": "No Results Found", "owner": "-", "sns": "-", "url": "-", "description": "-"}])
    
    df.write_csv("curator_list.csv")
    print(f"DONE: {len(df)} curators saved to curator_list.csv")