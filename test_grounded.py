"""Test if chatbot answers are grounded in knowledge base vs general knowledge."""
import httpx, json, sys

BASE = "https://chatbot.activiity.com"

def test_question(label, question, mode="naive", exp_grounded=True):
    print(f'\n--- {label} ---')
    print(f'Q: {question}')
    
    # Call the compare endpoint
    payload = {
        "question": question,
        "mode": mode,
        "models": ["qwen/qwen3-8b"],
        "tier": "reference"
    }
    
    try:
        r = httpx.post(f"{BASE}/api/chat/compare", json=payload, timeout=60)
        if r.status_code != 200:
            print(f'  HTTP {r.status_code}: {r.text[:100]}')
            return
        
        data = r.json()
        results = data.get('results', [])
        if not results:
            print('  No results returned')
            return
        
        answer = results[0].get('answer', '')
        print(f'A: {answer[:200]}')
        
        # Check for refusal
        is_refusal = 'ne trouve pas' in answer.lower() or 'not found' in answer.lower()
        
        if exp_grounded and is_refusal:
            print(f'  WARNING: Expected grounded answer but got refusal')
        elif not exp_grounded and not is_refusal:
            print(f'  WARNING: Expected refusal but got an answer')
        elif exp_grounded and not is_refusal:
            print(f'  OK: Answer provided (likely grounded)')
        else:
            print(f'  OK: Correctly refused out-of-scope question')
            
    except Exception as e:
        print(f'  ERROR: {e}')

# Test 1: Question from knowledge base (UA-1 Delegation)
test_question("In-knowledge-base (UA-1)", 
    "Quels sont les quatre sources de frustration du manager qui délègue ?",
    exp_grounded=True)

# Test 2: Question that should be out of scope
test_question("Out-of-scope",
    "Quel est le cours de l'or aujourd'hui ?",
    exp_grounded=False)

# Test 3: Another knowledge base question (UA-5)
test_question("In-knowledge-base (UA-5)",
    "Comment reconnaître une mauvaise ambiance dans une équipe ?",
    exp_grounded=True)
