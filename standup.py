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

# Function to call ChatGPT for stand-up performer extraction
def get_standup_performer(event_name, event_desc, existing_artist):
    prompt = f"""
Event Name: "{event_name}"
Event Description: "{event_desc}"
Existing Performer Name: "{existing_artist}"

Extract only the name(s) of the stand-up comedian(s) performing at this event.  
Ignore words like "feat.", "live", "stand-up show", or venue details.  
If multiple comedians are performing, return only their names, separated by commas.  
If the existing value in 'Sanatçı Adı' is incorrect, correct it.  
Provide a confidence score from 0 to 100 based on how sure you are.  

Format response as:  
Performer: [corrected performer names]  
Confidence: [confidence score]
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        text_response = response.choices[0].message.content  # Extract content
        
        # Parse the response
        lines = text_response.split("\n")
        performer_line = next((line for line in lines if line.startswith("Performer:")), "Performer: ")
        confidence_line = next((line for line in lines if line.startswith("Confidence:")), "Confidence: 0")
        
        performer_names = performer_line.replace("Performer: ", "").strip()
        confidence = confidence_line.replace("Confidence: ", "").strip()

        return performer_names, confidence
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

    # Skip rows that are already confirmed or not in "Stand-up" category
    if confirmed in ["1", "0.8"] or category.lower() != "stand-up":
        continue

    # Skip empty event names
    if not event_name.strip():
        continue

    # Get corrected performer name from ChatGPT
    corrected_artist, confidence = get_standup_performer(event_name, event_desc, existing_artist)

    # Update row only if confidence is above 75%
    if corrected_artist and float(confidence) > 75:
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

print("🎭 All relevant 'Stand-up' rows updated in the original file!")
