import asyncio
import json

from flask import Flask, render_template, request, jsonify
from agents import ChefAgent

app = Flask(__name__)

def transform_agent_output(diet_json_str, shopping_json_str, recipe_json_str):
    """
    Parses raw JSON strings from agents and converts them into the 
    structure expected by the frontend.
    """
    # 1. Parse the strings into Python Dictionaries
    # We use empty dicts/lists as fallbacks if parsing fails or data is None
    try:
        diet_data = json.loads(diet_json_str) if diet_json_str else {}
        shopping_data = json.loads(shopping_json_str) if shopping_json_str else {}
        recipe_data = json.loads(recipe_json_str) if recipe_json_str else {}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return {"error": "Invalid JSON format from agents"}

    # 2. Merge Nutrition Data
    # We need to combine 'total_dish_nutrition' (Amount) with 'percentage_of_daily_apport' (Daily Value)
    formatted_nutrition = []
    
    # Create a lookup dictionary for percentages for faster access
    # Key = Nutrient Name, Value = Percentage String (e.g. "28.52%")
    percent_map = {
        item['nutrient_name']: item['nutrient_quantity'] 
        for item in diet_data.get('percentage_of_daily_apport', [])
    }

    # Iterate through the absolute amounts and link them to percentages
    for item in diet_data.get('total_dish_nutrition', []):
        name = item.get('nutrient_name')
        amount = item.get('nutrient_quantity')
        
        # Look up the percentage, default to "-" if not found
        daily_value = percent_map.get(name, "-")

        formatted_nutrition.append({
            "name": name,
            "amount": amount,
            "daily_value": daily_value
        })

    # 3. Construct the Final Object
    final_output = {
        "recipe_name": recipe_data.get("dish_name", "Mystery Dish"),
        "missing_ingredients": shopping_data.get("items", []),
        "steps": recipe_data.get("dish_steps", []),
        "nutrition": formatted_nutrition
    }

    return final_output

def generate_recipe_logic(leftovers):
    chef = ChefAgent()

    try:
        print(f"👨‍🍳 Chef is thinking about: {leftovers}...")
        diet_output, shopping_list, recipe_steps = asyncio.run(chef.run(leftovers))

        def ensure_str(data):
            return json.dumps(data) if isinstance(data, (dict, list)) else data
        
        recipe_data = transform_agent_output(
            ensure_str(diet_output),
            ensure_str(shopping_list),
            ensure_str(recipe_steps)
        )
        
        return recipe_data
    
    except Exception as e:
        print(f"❌ Agent Error: {e}")
        # Fallback to a simple error message for the UI
        return {
            "recipe_name": "Error generating recipe",
            "missing_ingredients": [],
            "steps": ["Could not generate recipe. Please try again."],
            "nutrition": []
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    leftovers = data.get('leftovers', '')
    
    if not leftovers:
        return jsonify({"error": "Please provide leftovers"}), 400
        
    result = generate_recipe_logic(leftovers)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)