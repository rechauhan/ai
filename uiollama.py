
from bs4 import BeautifulSoup
import requests
from jinja2 import Environment, FileSystemLoader
import re
import json
with open("policy.json", "r", encoding="utf-8") as f:
    policy = json.load(f)


# Step 1: Extract UI elements
def extract_ui_elements(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
        soup = BeautifulSoup(html, 'html.parser')

    elements = []
    for tag in soup.find_all(['label', 'input', 'button']):
        text = tag.get_text(strip=True)
        if text:
            # Find line number (approximate)
            line_number = html[:html.find(str(tag))].count('\n') + 1
            parent = tag.find_parent()
            parent_name = parent.name if parent else None
            elements.append({
                'element_type': tag.name,
                'element_text': text,
                'line_number': line_number,
                'parent': parent_name
            })
    for option in soup.find_all('option'):
        option_text = option.get_text(strip=True)
        if option_text:
            line_number = html[:html.find(str(option))].count('\n') + 1
            parent = option.find_parent()
            parent_name = parent.name if parent else None
            elements.append({
                'element_type': 'option',
                'element_text': option_text,
                'line_number': line_number,
                'parent': parent_name
            })
    return elements
# Step 2: Validate with Ollama API
def validate_with_llm(element, policy):
    # Use LLM for all compliance checks, including prohibited terms
    prompt = f"""
You are a UI compliance auditor. For the following UI element, check if its text contains any prohibited terms from this list: {policy['prohibited_terms']}.
Also check if it contains any required phrases from this list: {policy['required_phrases']}.
Also check accessibility guidelines.

Element Type: {element['element_type']}
Element Text: {element['element_text']}
Line Number: {element.get('line_number', '')}
Parent Tag: {element.get('parent', '')}

Policy:
- Prohibited terms: {policy['prohibited_terms']}
- Required phrases: {policy['required_phrases']}
- Accessibility guidelines: {policy['accessibility_guidelines']}

Respond with:
- Compliance Status: Compliant / Needs Review / Non-Compliant
- Reason (always specify why if Non-Compliant, including which prohibited term or required phrase is missing)
- Suggested Correction (if any)
"""
    api_url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(api_url, json=payload)
    if response.status_code != 200:
        print("Ollama API error:", response.status_code, response.text)
        return ""
    try:
        result = response.json()
        generated_text = result.get("response", "")
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