from scripts.extract_concert_artists import process_concerts
from scripts.extract_standup_comedians import process_standups
from scripts.category_selection import process_category_selection
from scripts.category_selection import evaluate_ai_vs_manual
from scripts.category_selection import iterative_prompt_refinement
from scripts.category_selection import update_ai_match_status

if __name__ == "__main__":
    # print("🎵 Processing Concerts...")
    # process_concerts()  # Runs the concert artist extraction

    # print("\n🎭 Processing Stand-up Shows...")
    # process_standups()  # Runs the stand-up artist extraction

    print("\n🎭 Processing Event Categories...")
    process_category_selection()  # Handles category selection job
    evaluate_ai_vs_manual()
    
    # iterative_prompt_refinement()

    print("\n✅ All scripts completed!")
