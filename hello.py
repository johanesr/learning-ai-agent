from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=200,
    messages=[{"role": "user", "content": "Say hello in Bahasa Indonesia."}],
)
print(response.content[0].text)
print("---")
print(f"tokens in: {response.usage.input_tokens}, out: {response.usage.output_tokens}")
