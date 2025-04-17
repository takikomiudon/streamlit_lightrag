import os

import lyricsgenius
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("GENIUS_ACCESS_TOKEN")

genius = lyricsgenius.Genius(token)


def save_lyrics_for_artist(artist_name, max_songs=5):
    print(f"{artist_name}の曲を検索中...")

    artist = genius.search_artist(artist_name, max_songs=max_songs)

    if not artist:
        print(f"{artist_name}が見つかりませんでした。")
        return

    print(f"{len(artist.songs)}曲が見つかりました。")

    lyrics_dir = os.path.join(os.path.dirname(__file__), f"{artist_name}/input")
    os.makedirs(lyrics_dir, exist_ok=True)

    for song in artist.songs:
        safe_title = song.title.replace('/', '_').replace('\\', '_').replace(':', '_')
        file_name = f"{safe_title}.txt"
        file_path = os.path.join(lyrics_dir, file_name)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(song.lyrics)

        print(f"保存しました: {file_path}")

    return artist


if __name__ == "__main__":
    artist_name = 'サザンオールスターズ'

    max_songs = None

    artist = save_lyrics_for_artist(artist_name, max_songs)
    artist = save_lyrics_for_artist(artist_name, max_songs)
