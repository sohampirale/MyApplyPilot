import os
import urllib.request
import urllib.error
import json

def load_env_vars(env_path=".env"):
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip().strip("'\"")
    return env_vars

env_vars = load_env_vars()
api_key = env_vars.get("LLM_API_KEY") or os.getenv("LLM_API_KEY")
base_url = env_vars.get("LLM_URL") or os.getenv("LLM_URL", "https://api.deepseek.com")

if not api_key:
    print("Error: LLM_API_KEY not found in .env file or environment.")
    exit(1)

url = f"{base_url.rstrip('/')}/user/balance"
req = urllib.request.Request(
    url,
    headers={
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    },
    method="GET"
)

try:
    with urllib.request.urlopen(req) as response:
        if response.status == 200:
            data = json.loads(response.read().decode("utf-8"))
            print("=== DeepSeek API Balance Information ===")
            print(f"Is Available: {data.get('is_available')}")
            for info in data.get("balance_infos", []):
                print(f"Currency: {info.get('currency')}")
                print(f"Total Balance: {info.get('total_balance')}")
                print(f"Granted Balance (Bonus): {info.get('granted_balance')}")
                print(f"Topped-Up Balance (Paid): {info.get('topped_up_balance')}")
        else:
            print(f"Response Status: {response.status}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error ({e.code}): {e.read().decode('utf-8')}")
except Exception as e:
    print(f"An error occurred: {e}")

