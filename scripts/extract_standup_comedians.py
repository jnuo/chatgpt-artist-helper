import time
from utils.csv_handler import read_csv, write_csv
from utils.artist_extractor import extract_standup_artist

CSV_FILE = "artist.csv"

def process_standups():
    """Processes all stand-up shows and updates performer names."""
    data = read_csv(CSV_FILE)
    fieldnames = list(data[0].keys())  # Convert dict_keys to list

    # Ensure required columns exist
    for col in ["Old Sanatçı Adı", "Confirmed?", "Confidence Score"]:
        if col not in fieldnames:
            fieldnames.append(col)
            for row in data:
                row[col] = ""  # Initialize empty values

    for index, row in enumerate(data):
        # Only process Stand-up shows
        if row["cat"] != "Stage" or row["subcat"] != "Standup":
            continue

        # Skip already confirmed rows
        if row.get("Confirmed?") in ["1", "0.8"]:
            continue

        old_artist = row["Sanatçı Adı"]
        corrected_artist, confidence = extract_standup_artist(row["name"], row["desc"], old_artist)

        # Convert confidence to float for comparison
        confidence = float(confidence) if confidence else 0.0  

        if confidence >= 0.75:
            if corrected_artist and corrected_artist != old_artist:
                row["Old Sanatçı Adı"] = old_artist  # Store old value
            row["Sanatçı Adı"] = corrected_artist  # Update performer name
            row["Confirmed?"] = "0.8"  # Mark as processed
        else:
            row["Sanatçı Adı"] = ""  # Clear performer name if confidence is low

        row["Confidence Score"] = confidence  # Store confidence score

        write_csv(CSV_FILE, data, fieldnames)
        print(f"✅ {row['name']} → {corrected_artist if confidence >= 0.75 else '❌ Not confident'} (Confidence: {confidence})")

        time.sleep(15)

if __name__ == "__main__":
    process_standups()
