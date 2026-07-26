import base64
import json
import urllib.request
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

IMAGE_PATH = os.path.join("src", "assets", "image.png")

def test_groq_monkey_api():
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: Could not find image at {IMAGE_PATH}")
        return

    with open(IMAGE_PATH, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    mime_type = "image/png"
    if IMAGE_PATH.endswith(".jpg") or IMAGE_PATH.endswith(".jpeg"):
        mime_type = "image/jpeg"
        
    image_data_url = f"data:{mime_type};base64,{encoded_string}"

    prompt_text = (
        "These images are taken from a phone screen so the image quality might be bad, "
        "but if it has a monkey then answer strictly with 'YES', otherwise answer strictly with 'NO'."
    )

    api_url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")
    model_name = "qwen/qwen3.6-27b"

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        }
                    }
                ]
            }
        ]
    }

    print(f"Sending image ({os.path.getsize(IMAGE_PATH)} bytes) to Groq API ({model_name})...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            answer = result['choices'][0]['message']['content'].strip()
            print("\n" + "="*50)
            print(f"GROQ API RESPONSE: {answer}")
            print("="*50)
            if "YES" in answer.upper():
                print("SUCCESS: MONKEY DETECTED IN IMAGE!")
            else:
                print("INFO: NO MONKEY DETECTED IN IMAGE.")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_groq_monkey_api()
