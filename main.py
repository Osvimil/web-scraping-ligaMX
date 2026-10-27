import csv
import unicodedata
from pathlib import Path
import requests
from bs4 import BeautifulSoup

URL = "https://ligamx.net/cancha/tablas/" "tablaGoleoCompleta/sp/c3fc339bb2fd67"

OUTPUT_FILE = Path(__file__).resolve().parent / "ligamx_goleadores.csv"


def normalize_text(text):
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character for character in text if not unicodedata.combining(character)
    )
    return text


def download_page(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def find_scorers_table(soup):
    tables = soup.find_all("table")
    for table in tables:
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            headings = [
                normalize_text(cell.get_text(" ", strip=True)) for cell in cells
            ]
            required_headings = {"jugador", "club", "g", "nacionalidad"}
            if required_headings.issubset(set(headings)):
                return table, headings
    return None, None


def extract_scorers(soup):
    table, headings = find_scorers_table(soup)
    if table is None:
        raise ValueError(
            "The top-scorers table was not found"
            "The page structure may have changed, or the web site "
            "may be returning HTML without the table"
        )
    column_positions = {heading: index for index, heading in enumerate(headings)}
    player_index = column_positions["jugador"]
    club_index = column_positions["club"]
    goals_index = column_positions["g"]
    nationality_index = column_positions["nacionalidad"]

    players = []

    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        values = [cell.get_text(" ", strip=True) for cell in cells]
        required_indexes = [player_index, club_index, goals_index, nationality_index]

        if not values or max(required_indexes) >= len(values):
            continue
        player_name = values[player_index]
        club_name = values[club_index]
        goals_text = values[goals_index]
        nationality = values[nationality_index]

        if normalize_text(player_name) == "jugador":
            continue
        if not player_name or not club_name or not nationality:
            continue
        try:
            goals = int(goals_text.replace(",", "").strip())
        except ValueError:
            continue
        player = {
            "player_name": player_name,
            "team": club_name,
            "goals": goals,
            "nationality": nationality,
        }
        players.append(player)
    return players


def save_to_csv(players, output_file):
    fieldnames = ["player_name", "team", "goals", "nationality"]
    with output_file.open(mode="w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(players)


def main():
    print("Starting Liga MX web scraping...")
    print(f"Website: {URL}")
    html = download_page(URL)
    print(f"HTML downloaded: {len(html)} characters")
    soup = BeautifulSoup(html, "html.parser")
    players = extract_scorers(soup)
    if not players:
        raise ValueError(
            "The table was found but no player records were "
            "extracted. Check the HTML structure"
        )
    save_to_csv(players, OUTPUT_FILE)
    print(f"\nPlayers extracted: {len(players)}")
    print(f"CSV files saved to: {OUTPUT_FILE}")
    print("\nPreview of the first five players:")

    for player in players[:5]:
        print(
            f"{player['player_name']} | "
            f"{player['team']} | "
            f"{player['goals']} goals | "
            f"{player['nationality']} | "
        )


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as error:
        print(f"Network or HTTP error: {error}")
    except ValueError as error:
        print(f"Scraping error: {error}")
