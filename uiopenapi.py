# ui_checker.py
from bs4 import BeautifulSoup
import requests
from jinja2 import Environment, FileSystemLoader
import re

# Sample policy
policy = {
    "prohibited_terms": ["Superuser", "Submit Now"],
    "required_phrases": ["Email Address", "User Role"],
    "accessibility_guidelines": ["Use alt text", "Ensure contrast ratio"]
}

# Step 1: Extract UI elements
def extract_ui_elements(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    elements = []
    for tag in soup.find_all(['label', 'input', 'select', 'option', 'button']):
        text = tag.get_text(strip=True)
        if text:
            elements.append({
                'element_type': tag.name,
                'element_text': text
            })
    return elements

# Step 2: Validate with OpenAI API
def validate_with_llm(element, policy):
    prompt = f"""
You are a UI compliance auditor. Check if the following UI element text complies with company policy.

Element Type: {element['element_type']}
Element Text: {element['element_text']}
Policy:
- Prohibited terms: {policy['prohibited_terms']}
- Required phrases: {policy['required_phrases']}
- Accessibility guidelines: {policy['accessibility_guidelines']}

Respond with:
- Compliance Status: Compliant / Needs Review / Non-Compliant
- Reason
- Suggested Correction (if any)
"""
    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": "Bearer sk-xx",  # Replace with your OpenAI API key
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 512
    }
    response = requests.post(api_url, headers=headers, json=payload)
    if response.status_code != 200:
        print("OpenAI API error:", response.status_code, response.text)
        return ""
    try:
        result = response.json()
        generated_text = result["choices"][0]["message"]["content"]
    except Exception as e:
        print("JSON decode error:", e)
        return ""
    return generated_text

# Step 3: Parse LLM response
def parse_llm_response(response):
    status_match = re.search(r"Compliance Status:\s*(.*)", response)
    reason_match = re.search(r"Reason:\s*(.*)", response)
    suggestion_match = re.search(r"Suggested Correction:\s*(.*)", response)

    status = status_match.group(1).strip() if status_match else "Unknown"
    reason = reason_match.group(1).strip() if reason_match else ""
    suggestion = suggestion_match.group(1).strip() if suggestion_match else ""

    status_class = {
        "Compliant": "compliant",
        "Non-Compliant": "non-compliant",
        "Needs Review": "needs-review"
    }.get(status, "")

    return status, reason, suggestion, status_class

# Step 4: Generate dashboard
def generate_dashboard(results, output_path):
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('dashboard_template.html')
    html = template.render(results=results)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

# Step 5: Run the pipeline
elements = extract_ui_elements("input_ui.html")
results = []

for element in elements:
    response = validate_with_llm(element, policy)
    status, reason, suggestion, status_class = parse_llm_response(response)
    results.append({
        "element_type": element["element_type"],
        "element_text": element["element_text"],
        "status": status,
        "reason": reason,
        "suggestion": suggestion,
        "status_class": status_class
    })

generate_dashboard(results, "output_report.html")
print("✅ Compliance report generated: output_report.html")