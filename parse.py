from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# 🔧 Improved Prompt Template
template = """Extract the following information: {parse_description}
From this content:
{dom_content}

Requirements:
1. Extract ALL matches found in the content.
2. Return the results as a newline-separated list.
3. If no matches are found, return an empty string.
4. Do not include "not found" messages or conversational text.
5. Do not include bullet points or numbering, just the data values."""

def get_llm(api_key=None, model_name=None):
    return ChatGroq(
        model=model_name or "llama-3.3-70b-versatile",
        api_key=api_key
    )

def parse_content(dom_chunks, parse_description, api_key=None, model_name=None):
    """
    Parse text chunks using Groq
    """
    llm = get_llm(api_key, model_name)
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    parsed_results = []

    for i, chunk in enumerate(dom_chunks, start=1):
        print(f"🧠 Processing batch {i}/{len(dom_chunks)}...")
        
        try:
            response = chain.invoke({
                "dom_content": chunk,  # Pass the full chunk
                "parse_description": parse_description
            })
            
            # Extract text from response
            if hasattr(response, 'content'):
                result_text = response.content.strip()
            elif isinstance(response, str):
                result_text = response.strip()
            else:
                result_text = str(response).strip()
            
            # Split by newline to get individual items
            items = [item.strip() for item in result_text.split('\n') if item.strip()]
            
            # Filter out common "not found" phrases
            clean_items = []
            for item in items:
                clean_item = item.lower().strip('"').strip("'")
                if clean_item not in ['none', 'no data found', 'n/a', 'no information found', '', 'empty string']:
                    clean_items.append(item.strip('"').strip("'"))
            
            parsed_results.extend(clean_items)
            
        except Exception as e:
            print(f"⚠️ Error in batch {i}: {e}")
            # No action needed, just skip

    return parsed_results  # Return flat list of all extracted items