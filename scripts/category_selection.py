from utils.google_sheets import get_sheet_data
from utils.openai_client import get_chatgpt_response
import gspread
import json
import time
from google.oauth2.service_account import Credentials
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()

# These should match your utils/google_sheets.py
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

# --- Utility Functions ---
def get_gspread_client():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return gspread.authorize(creds)

def get_worksheet(client, sheet_name):
    return client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)

def get_all_rows(sheet):
    data = sheet.get_all_values()
    header = data[0]
    rows = data[1:]
    return header, rows

def ensure_result_dict_sheet(client):
    # Create or get the result_dict sheet with correct columns
    try:
        result_sheet = client.open_by_key(SPREADSHEET_ID).worksheet('result_dict')
    except gspread.exceptions.WorksheetNotFound:
        result_sheet = client.open_by_key(SPREADSHEET_ID).add_worksheet(title='result_dict', rows="1000", cols="5")
        result_sheet.append_row(['id', 'event_name', 'new_cat', 'new_subcat1', 'new_subcat2'])
    return result_sheet

def read_result_dict_to_df(result_sheet):
    result_data = result_sheet.get_all_values()
    if len(result_data) <= 1:
        return pd.DataFrame(columns=['id', 'event_name', 'new_cat', 'new_subcat1', 'new_subcat2'])
    df = pd.DataFrame(result_data[1:], columns=result_data[0])
    return df

def append_batch_to_result_sheet(result_sheet, batch_df):
    # Appends a batch DataFrame to the result_dict sheet in one call
    if batch_df.empty:
        return
    values = batch_df[['id', 'event_name', 'new_cat', 'new_subcat1', 'new_subcat2']].values.tolist()
    result_sheet.append_rows(values, value_input_option='USER_ENTERED')

# --- Main Processing Function ---
def process_category_selection():
    print("\n📋 Reading Google Sheet for Category Selection...")
    sheet_name = 'all_events'
    client = get_gspread_client()
    sheet = get_worksheet(client, sheet_name)
    header, rows = get_all_rows(sheet)
    col_idx = {col: i for i, col in enumerate(header)}
    batch_size = 50

    # Prepare result_dict sheet and read existing results
    result_sheet = ensure_result_dict_sheet(client)
    result_df = read_result_dict_to_df(result_sheet)
    existing_ids = set(result_df['id'])

    # Prepare batch
    batch = []
    with open("prompt_template.txt", "r", encoding="utf-8") as f:
        prompt_template = f.read()

    for idx, row in enumerate(rows):
        row_id = row[col_idx['id']]
        # Skip if already processed
        if row_id in existing_ids:
            continue
        event_name = row[col_idx['event_name']]
        # Check if ai_new_subcat1 is already filled in all_events
        ai_new_cat_val = row[col_idx.get('ai_new_cat', -1)].strip() if 'ai_new_cat' in col_idx else ''
        ai_new_subcat1_val = row[col_idx.get('ai_new_subcat1', -1)].strip() if 'ai_new_subcat1' in col_idx else ''
        ai_new_subcat2_val = row[col_idx.get('ai_new_subcat2', -1)].strip() if 'ai_new_subcat2' in col_idx else ''
        if ai_new_subcat1_val:
            # Use existing AI values from all_events
            batch.append({'id': row_id, 'event_name': event_name, 'new_cat': ai_new_cat_val, 'new_subcat1': ai_new_subcat1_val, 'new_subcat2': ai_new_subcat2_val})
            print(f"Used cached AI values for row {idx+2} (id={row_id}) | Event: '{event_name}' | AI Category: '{ai_new_cat_val}' | AI Subcat1: '{ai_new_subcat1_val}'")
        else:
            event_desc = row[col_idx['event_desc']]
            prompt = prompt_template.format(event_name=event_name, event_desc=event_desc)
            ai_response = get_chatgpt_response(prompt)
            import re
            ai_response_clean = ai_response.strip()
            match = re.search(r"```(?:json)?\n([\s\S]+?)\n?```", ai_response_clean)
            if match:
                ai_response_clean = match.group(1).strip()
            try:
                ai_json = json.loads(ai_response_clean)
            except Exception as e:
                print(f"Error parsing AI response for row {idx+2}: {ai_response}")
                continue  # skip this row if parsing fails
            ai_new_cat = ai_json.get('new_cat', '')
            ai_new_subcat1 = ai_json.get('new_subcat1', '')
            ai_new_subcat2 = ai_json.get('new_subcat2', '')
            batch.append({'id': row_id, 'event_name': event_name, 'new_cat': ai_new_cat, 'new_subcat1': ai_new_subcat1, 'new_subcat2': ai_new_subcat2})
            print(f"Prepared row {idx+2} (id={row_id}) | Event: '{event_name}' | AI Category: '{ai_new_cat}' | AI Subcat1: '{ai_new_subcat1}'")
        if len(batch) == batch_size:
            batch_df = pd.DataFrame(batch)
            append_batch_to_result_sheet(result_sheet, batch_df)
            print(f"Batch of {batch_size} written to 'result_dict'. IDs: {batch_df['id'].tolist()}")
            # Update in-memory result_df and ID set
            result_df = pd.concat([result_df, batch_df], ignore_index=True)
            existing_ids.update(batch_df['id'])
            batch = []
    # Write any remaining rows
    if batch:
        batch_df = pd.DataFrame(batch)
        append_batch_to_result_sheet(result_sheet, batch_df)
        print(f"Final batch written to 'result_dict'. IDs: {batch_df['id'].tolist()}")

def evaluate_ai_vs_manual():
    """
    Compare ai_new_subcat1/ai_new_subcat2 columns with new_subcat1/new_subcat2 columns.
    Print statistics: total manually labeled, exact matches, partial matches (order-insensitive).
    Only analyze rows where both new_cat and new_subcat1 are not empty.
    """
    print("\n📊 Evaluating AI vs. Manual Subcategory Labels...")
    sheet_name = 'all_events'
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        data = sheet.get_all_values()
        header = data[0]
        rows = data[1:]
        col_idx = {col: i for i, col in enumerate(header)}
        total_manual = 0
        exact_match = 0
        partial_match = 0
        status_updates = []
        for idx, row in enumerate(rows):
            manual_cat = row[col_idx.get('new_cat', -1)].strip() if 'new_cat' in col_idx else ''
            manual_1 = row[col_idx.get('new_subcat1', -1)].strip() if 'new_subcat1' in col_idx else ''
            manual_2 = row[col_idx.get('new_subcat2', -1)].strip() if 'new_subcat2' in col_idx else ''
            ai_1 = row[col_idx.get('ai_new_subcat1', -1)].strip() if 'ai_new_subcat1' in col_idx else ''
            ai_2 = row[col_idx.get('ai_new_subcat2', -1)].strip() if 'ai_new_subcat2' in col_idx else ''
            match_status = "NO MATCH"
            if manual_cat and manual_1:
                total_manual += 1
                manual_set = set(filter(None, [manual_1, manual_2]))
                ai_set = set(filter(None, [ai_1, ai_2]))
                if manual_set == ai_set and manual_set:
                    exact_match += 1
                    match_status = "EXACT"
                elif manual_set & ai_set:
                    partial_match += 1
                    match_status = "PARTIAL"
            status_updates.append(match_status)
        print(f"Total manually labeled rows: {total_manual}")
        print(f"Exact matches (order-insensitive): {exact_match}")
        print(f"Partial matches (any overlap, order-insensitive): {partial_match}")
        print(f"No match: {total_manual - exact_match - partial_match}")
    except Exception as e:
        print(f"Error reading or updating Google Sheet: {e}")

def suggest_better_prompt_from_disagreements(max_examples=25):
    """
    Extract disagreement cases between manual and AI subcategory labels,
    upload them to the latest OpenAI GPT model, and ask for a better prompt
    including example cases from the data. Adds explicit instruction to use Turkish culture and ticketing sites.
    """
    print("\n🤖 Generating improved prompt using ChatGPT based on disagreement cases...")
    sheet_name = 'all_events'
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        data = sheet.get_all_values()
        header = data[0]
        rows = data[1:]
        col_idx = {col: i for i, col in enumerate(header)}
        # Gather all disagreement cases based on ai_match_status == 'NO MATCH'
        disagreements = []
        for row in rows:
            match_status = row[col_idx.get('ai_match_status', -1)].strip() if 'ai_match_status' in col_idx else ''
            if match_status != 'NO MATCH':
                continue
            manual_1 = row[col_idx.get('new_subcat1', -1)].strip() if 'new_subcat1' in col_idx else ''
            manual_2 = row[col_idx.get('new_subcat2', -1)].strip() if 'new_subcat2' in col_idx else ''
            ai_1 = row[col_idx.get('ai_new_subcat1', -1)].strip() if 'ai_new_subcat1' in col_idx else ''
            ai_2 = row[col_idx.get('ai_new_subcat2', -1)].strip() if 'ai_new_subcat2' in col_idx else ''
            disagreements.append({
                'event_name': row[col_idx.get('event_name', -1)],
                'event_desc': row[col_idx.get('event_desc', -1)],
                'manual_subcat1': manual_1,
                'manual_subcat2': manual_2,
                'ai_subcat1': ai_1,
                'ai_subcat2': ai_2
            })
        if not disagreements:
            print("No disagreement cases found!")
            return
        sample_disagreements = disagreements[:max_examples]
        # Prepare prompt for ChatGPT with Turkish/cultural context
        prompt = (
            "You are an expert event classifier for Turkish events. Use your knowledge of Turkish culture, language, and event norms. "
            "Consider how events are typically categorized on Turkish ticketing platforms such as biletinial.com and biletix.com. "
            "Here are some events where my manual subcategory labels differ from your AI predictions. For each event, see the event name, description, my manual labels, and your predictions. "
            "Analyze these disagreements and suggest a new, improved prompt for ChatGPT that would help the AI match my labeling style better. "
            "Include explicit rules and at least 3 representative examples from the data in your suggested prompt.\n\n"
        )
        for i, case in enumerate(sample_disagreements, 1):
            prompt += (
                f"Example {i}:\n"
                f"Event: {case['event_name']}\n"
                f"Description: {case['event_desc']}\n"
                f"Manual: {case['manual_subcat1']}, {case['manual_subcat2']}\n"
                f"AI: {case['ai_subcat1']}, {case['ai_subcat2']}\n\n"
            )
        prompt += (
            "\nPlease return only your improved prompt as a markdown code block, nothing else."
        )
        from utils.openai_client import get_chatgpt_response
        improved_prompt = get_chatgpt_response(prompt, model="gpt-4o")
        print("\n===== SUGGESTED IMPROVED PROMPT FROM CHATGPT =====\n")
        print(improved_prompt)
        print("\n===============================================\n")
    except Exception as e:
        print(f"Error during prompt suggestion: {e}")

def iterative_prompt_refinement(batch_size=25, prompt_file='prompt_template.txt', output_file='prompt_refinement_versions.txt', final_output_file='prompt_template_final.txt'):
    """
    Iteratively refine the prompt using all disagreement cases in batches.
    Each iteration sends the current prompt and a batch of disagreements to GPT-4o,
    and writes each improved prompt version to the output file.
    At the end, one final refinement is performed to remove duplicates and further improve the prompt.
    """
    import os
    print("\n🔄 Iterative prompt refinement starting...")
    sheet_name = 'all_events'
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        data = sheet.get_all_values()
        header = data[0]
        rows = data[1:]
        col_idx = {col: i for i, col in enumerate(header)}
        # Load initial prompt
        if not os.path.exists(prompt_file):
            print(f"Prompt file '{prompt_file}' not found!")
            return
        with open(prompt_file, 'r', encoding='utf-8') as f:
            current_prompt = f.read()
        # Gather all disagreement cases
        disagreements = []
        for row in rows:
            match_status = row[col_idx.get('ai_match_status', -1)].strip() if 'ai_match_status' in col_idx else ''
            if match_status != 'NO MATCH':
                continue
            manual_1 = row[col_idx.get('new_subcat1', -1)].strip() if 'new_subcat1' in col_idx else ''
            manual_2 = row[col_idx.get('new_subcat2', -1)].strip() if 'new_subcat2' in col_idx else ''
            ai_1 = row[col_idx.get('ai_new_subcat1', -1)].strip() if 'ai_new_subcat1' in col_idx else ''
            ai_2 = row[col_idx.get('ai_new_subcat2', -1)].strip() if 'ai_new_subcat2' in col_idx else ''
            disagreements.append({
                'event_name': row[col_idx.get('event_name', -1)],
                'event_desc': row[col_idx.get('event_desc', -1)],
                'manual_subcat1': manual_1,
                'manual_subcat2': manual_2,
                'ai_subcat1': ai_1,
                'ai_subcat2': ai_2
            })
        if not disagreements:
            print("No disagreement cases found!")
            return
        # Prepare output file
        with open(output_file, 'w', encoding='utf-8') as outf:
            batch_count = (len(disagreements) + batch_size - 1) // batch_size
            for batch_idx in range(batch_count):
                batch = disagreements[batch_idx*batch_size:(batch_idx+1)*batch_size]
                print(f"Processing batch {batch_idx+1}/{batch_count} with {len(batch)} disagreement cases...")
                prompt = (
                    "Below is my current event categorization prompt for Turkish events. "
                    "After that, you will see a batch of disagreement cases where my manual subcategory labels differ from your AI predictions. "
                    "Your task: Carefully analyze these disagreements and update the prompt to better match my labeling style. "
                    "You must NOT break or contradict existing rules, only improve, clarify, or expand them as needed. "
                    "The improved prompt MUST NOT exceed 10,000 characters. Before returning, re-read your improved prompt: remove duplicate or redundant text, merge similar or unnecessary separate rules, and ensure the prompt is always crisp, clear, and under 10,000 characters. If needed, condense, merge, or remove less important rules and examples, and keep only the most important and representative ones. "
                    "If you must omit details to stay under the limit, prioritize the most critical and representative instructions and examples. "
                    "Return ONLY the improved prompt as a markdown code block, and nothing else.\n\n"
                )
                prompt += "CURRENT PROMPT:\n" + current_prompt + "\n\n"
                for i, case in enumerate(batch, 1):
                    prompt += (
                        f"Example {i}:\n"
                        f"Event: {case['event_name']}\n"
                        f"Description: {case['event_desc']}\n"
                        f"Manual: {case['manual_subcat1']}, {case['manual_subcat2']}\n"
                        f"AI: {case['ai_subcat1']}, {case['ai_subcat2']}\n\n"
                    )
                prompt += ("\nPlease return only your improved prompt as a markdown code block, nothing else.")
                from utils.openai_client import get_chatgpt_response
                improved_prompt = get_chatgpt_response(prompt, model="gpt-4o")
                # Print character count for the improved prompt
                print(f"AI improved prompt length: {len(improved_prompt)} characters")
                outf.write(f"\n===== PROMPT VERSION {batch_idx+1} =====\n")
                outf.write(improved_prompt.strip() + "\n")
                import re
                match = re.search(r'```(?:[a-zA-Z]*)?\n([\s\S]+?)\n```', improved_prompt)
                if match:
                    current_prompt = match.group(1).strip()
                else:
                    print("Warning: Could not extract prompt code block from AI response.")
        # Final deduplication/refinement step
        print("\n✨ Performing final deduplication and refinement of the prompt...")
        final_prompt_instruction = (
            "Below is the latest version of my event categorization prompt for Turkish events. "
            "Please carefully review it, remove any duplicate or redundant rules or statements, and refine the language for clarity and conciseness. "
            "Do NOT remove any important rules or change the intended classification logic—just make the prompt as clear, non-repetitive, and effective as possible. "
            "Return only the improved prompt as a markdown code block.\n\n"
        )
        final_prompt_instruction += "CURRENT PROMPT:\n" + current_prompt + "\n\nPlease return only your improved prompt as a markdown code block, nothing else."
        from utils.openai_client import get_chatgpt_response
        final_prompt = get_chatgpt_response(final_prompt_instruction, model="gpt-4o")
        # Print the final refined prompt and its character length
        print(f"\nFinal refined prompt length: {len(final_prompt.strip())} characters\n")
        # Save the final version
        with open(final_output_file, 'w', encoding='utf-8') as f:
            f.write(final_prompt.strip() + "\n")
        print(f"\nFinal refined prompt written to '{final_output_file}'. Review and use as your new default if you like it!")
    except Exception as e:
        print(f"Error during iterative prompt refinement: {e}")

def update_ai_match_status():
    """
    Authenticates and updates the 'ai_match_status' column for all rows where 'new_subcat1' is not empty.
    The match status is calculated by comparing the set of manual subcats (new_subcat1, new_subcat2)
    with the set of AI subcats (ai_new_subcat1, ai_new_subcat2), order-insensitive.
    """
    sheet_name = 'all_events'
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        data = sheet.get_all_values()
        header = data[0]
        rows = data[1:]
        col_idx = {col: i for i, col in enumerate(header)}
        updated_rows = []
        for idx, row in enumerate(rows):
            manual_1 = row[col_idx.get('new_subcat1', -1)].strip() if 'new_subcat1' in col_idx else ''
            manual_2 = row[col_idx.get('new_subcat2', -1)].strip() if 'new_subcat2' in col_idx else ''
            ai_1 = row[col_idx.get('ai_new_subcat1', -1)].strip() if 'ai_new_subcat1' in col_idx else ''
            ai_2 = row[col_idx.get('ai_new_subcat2', -1)].strip() if 'ai_new_subcat2' in col_idx else ''
            if not manual_1:
                continue  # Only update if manual new_subcat1 is not empty
            manual_set = set(filter(None, [manual_1, manual_2]))
            ai_set = set(filter(None, [ai_1, ai_2]))
            match_status = "NO MATCH"
            if manual_set:
                if manual_set == ai_set and manual_set:
                    match_status = "EXACT"
                elif manual_set & ai_set:
                    match_status = "PARTIAL"
            # Update the ai_match_status column
            if 'ai_match_status' in col_idx:
                row_idx = idx + 2  # 1-based index, plus header
                sheet.update_cell(row_idx, col_idx['ai_match_status'] + 1, match_status)
                updated_rows.append(row_idx)
        print(f"Updated ai_match_status for {len(updated_rows)} rows.")
    except Exception as e:
        print(f"Error updating ai_match_status: {e}")

if __name__ == "__main__":
    process_category_selection()
    evaluate_ai_vs_manual()
    suggest_better_prompt_from_disagreements()
    iterative_prompt_refinement()
