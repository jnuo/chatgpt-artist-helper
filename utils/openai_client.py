import openai
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI API client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# def get_chatgpt_response(prompt, model="gpt-4"):
def get_chatgpt_response(prompt, model="gpt-4o"):
    """ChatGPT API çağrısı yaparak yanıt döndürür."""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()
