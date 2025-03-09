import openai
import csv
import time
import os
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI API Configuration
client = openai.OpenAI(api_key=OPENAI_API_KEY)  # New API client

# Input CSV file (modifying in place)
CSV_FILE = "artist.csv"

# Function to call ChatGPT for artist name extraction
def get_artist_name(event_name, event_desc, existing_artist):
    prompt = f"""
Event Name: "{event_name}"
Event Description: "{event_desc}"
Existing Artist Name: "{existing_artist}"

Extract only the artist name(s) from the event. Ignore extra words like "feat.", "live", or instrument details.  
If multiple artists exist, return only the names, comma-separated.  
If the existing artist value is incorrect, correct it.  
Also, provide a confidence score from 0 to 100 based on how sure you are.  

Format response as:  
Artist: [corrected artist names]  
Confidence: [confidence score]
"""
    try:
        response = client.chat.completions.create(  # Updated API call
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        text_response = response.choices[0].message.content  # Extract content
        
        # Parse the response
        lines = text_response.split("\n")
        artist_line = next((line for line in lines if line.startswith("Artist:")), "Artist: ")
        confidence_line = next((line for line in lines if line.startswith("Confidence:")), "Confidence: 0")
        
        artist_names = artist_line.replace("Artist: ", "").strip()
        confidence = confidence_line.replace("Confidence: ", "").strip()

        return artist_names, confidence
    except Exception as e:
        print(f"Error processing {event_name}: {e}")
        return "", "0"

# Read and update the CSV file row by row
with open(CSV_FILE, "r", encoding="utf-8") as infile:
    reader = list(csv.DictReader(infile))  # Convert to list for modifications

# Ensure 'Confidence Score' column exists
fieldnames = reader[0].keys()
if "Confidence Score" not in fieldnames:
    fieldnames = list(fieldnames) + ["Confidence Score"]  # Add new column header

# Process each row
for index, row in enumerate(reader):
    event_name = row["name"]
    event_desc = row["desc"]
    existing_artist = row["Sanatçı Adı"]
    confirmed = row["Confirmed?"].strip()
    category = row["cat"].strip()  # Read the category column

    # Skip rows that are already confirmed or not in "Concerts" category
    if confirmed in ["1", "0.8"] or category != "Concerts":
        continue

    # Skip empty event names
    if not event_name.strip():
        continue

    # Get corrected artist name from ChatGPT (now with event description!)
    corrected_artist, confidence = get_artist_name(event_name, event_desc, existing_artist)

    # Update row with new values if no error and confidence is higher than 0.75
    if corrected_artist and float(confidence) > 0.75:
        row["Sanatçı Adı"] = corrected_artist
        row["Confirmed?"] = "0.8"  # Mark as processed
    
    row["Confidence Score"] = confidence  # Store confidence score

    # Write updated data back to the file after processing each row
    with open(CSV_FILE, "w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)

    print(f"✅ Updated Row {index + 1}: {event_name} → {corrected_artist} (Confidence: {confidence})")

    # Wait 15 seconds before processing the next row
    time.sleep(15)

print("🎉 All relevant 'Concerts' rows updated in the original file!")
