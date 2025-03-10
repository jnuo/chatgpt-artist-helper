from utils.openai_client import get_chatgpt_response

def extract_concert_artist(event_name, event_desc, existing_artist):
    """Konser sanatçısını ChatGPT ile ayıklar."""
    prompt = f"""
Event Name: "{event_name}"
Event Description: "{event_desc}"
Existing Artist Name: "{existing_artist}"

Extract only the artist name(s) from the event. Ignore extra words like "feat.", "live", or instrument details.  
If multiple artists exist, return only the names, comma-separated.  
If the existing artist value is incorrect, correct it.  
Provide a confidence score from 0 to 100 based on how sure you are.

Format response as:  
Artist: [corrected artist names]  
Confidence: [confidence score]
"""
    response = get_chatgpt_response(prompt)
    return parse_response(response)

def extract_standup_artist(event_name, event_desc, existing_artist):
    """Stand-up komedyenini ChatGPT ile ayıklar."""
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
    response = get_chatgpt_response(prompt)
    return parse_response(response)

def parse_response(response):
    """ChatGPT yanıtını ayrıştırır."""
    if not response:
        return "", "0"
    
    lines = response.split("\n")
    artist_line = next((line for line in lines if line.startswith("Artist:") or line.startswith("Performer:")), "Artist: ")
    confidence_line = next((line for line in lines if line.startswith("Confidence:")), "Confidence: 0")
    
    artist_names = artist_line.split(": ")[1].strip()
    confidence = confidence_line.split(": ")[1].strip()

    return artist_names, confidence
