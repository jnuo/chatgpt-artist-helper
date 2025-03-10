from scripts.extract_concert_artists import process_concerts
from scripts.extract_standup_comedians import process_standups

if __name__ == "__main__":
    print("🎵 Processing Concerts...")
    process_concerts()  # Runs the concert artist extraction

    print("\n🎭 Processing Stand-up Shows...")
    process_standups()  # Runs the stand-up artist extraction

    print("\n✅ All scripts completed!")
