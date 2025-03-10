import time
from utils.csv_handler import read_csv, write_csv
from utils.artist_extractor import extract_concert_artist

CSV_FILE = "artist.csv"

def process_concerts():
    """Processes all concerts and updates artist names."""
    data = read_csv(CSV_FILE)
    fieldnames = list(data[0].keys())  # Convert dict_keys to list

    if "Old Sanatçı Adı" not in fieldnames:
        fieldnames.append("Old Sanatçı Adı")

    for index, row in enumerate(data):
        if row["cat"] != "Concerts":  # Only process concerts
            continue

        old_artist = row["Sanatçı Adı"]
        corrected_artist, confidence = extract_concert_artist(row["name"], row["desc"], old_artist)

        # Convert confidence to float for comparison
        confidence = float(confidence) if confidence else 0.0  

        if confidence >= 0.75:
            if corrected_artist and corrected_artist != old_artist:
                row["Old Sanatçı Adı"] = old_artist  # Store old value
            row["Sanatçı Adı"] = corrected_artist  # Update artist name
        else:
            row["Sanatçı Adı"] = ""  # Clear artist name if confidence is low

        row["Confidence Score"] = confidence  # Store confidence score

        write_csv(CSV_FILE, data, fieldnames)
        print(f"✅ {row['name']} → {corrected_artist if confidence >= 0.75 else '❌ Not confident'} (Confidence: {confidence})")

if __name__ == "__main__":
    process_concerts()
