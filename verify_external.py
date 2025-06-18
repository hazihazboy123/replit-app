import requests

# Test the exact endpoint you need to use in n8n
response = requests.post(
    "https://flashcard-converter-haziqmakesai.replit.app/api/generate-json",
    json={"deck_name": "Medical Flashcards", "cards": [{"front": "Test", "back": "Response"}]},
    headers={"Content-Type": "application/json"}
)

print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")
if response.status_code == 200:
    print("SUCCESS - Ready for n8n")
    print(f"Response: {response.json()}")
else:
    print(f"FAILED: {response.text}")