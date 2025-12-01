import os
import asyncio
from dotenv import load_dotenv

from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import AgentTool, google_search
from google.genai import types
from google.adk.code_executors import BuiltInCodeExecutor
from pydantic import BaseModel, Field
from google.adk.plugins.logging_plugin import (
    LoggingPlugin,
)

class ShoppingList(BaseModel):
    items: list[str] = Field(description="A list of missing food items to buy.")

class NutrientEntry(BaseModel):
    nutrient_name: str = Field(description="The name of the nutrient (e.g., 'Protein', 'Calories').")
    nutrient_quantity: str = Field(description="The measured or calculated quantity of the nutrient in unit.")

class NutritionAnalysis(BaseModel):
    
    total_dish_nutrition: list[NutrientEntry] = Field(
        description="A list detailing the total macro/micro nutrients provided by the dish."
    )
    daily_nutrient_needs_average_man: list[NutrientEntry] = Field(
        description="A list detailing the recommended daily intake for an average man."
    )
    percentage_of_daily_apport: list[NutrientEntry] = Field(
        description="A list detailing the percentage of the daily need covered by the dish."
    )

class RecipeDetails(BaseModel):
    dish_name: str = Field(description="The official name of the recipe (e.g., 'Healthy French Toast').")
    dish_steps: list[str] = Field(description="An ordered list of steps required to prepare the dish.")

class ChefAgent:
    def __init__(self):
        load_dotenv()
        os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
        self.retry_config= types.HttpRetryOptions(
            attempts=5,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429,500,503,504]
        )
        self.root_agent = self.create_agent()


    def create_agent(self):
        model_config = Gemini(model="gemini-2.5-flash-lite", retry_options=self.retry_config)

        leftover_parser_agent = Agent(
            name='LeftoverParser',
            model=model_config,
            instruction="Convert input to a dictionary of ingredients. Output must be ONLY JSON without markdown format",
            output_key="leftover_list"
        )

        recipe_thinker_agent = Agent(
            name='RecipeThinker',
            model=model_config,
            instruction="Find a healthy recipe using {leftover_list}.",
            tools=[google_search],
            output_key="recipe"
        )

        food_shopping_agent = Agent(
            name='FoodShopping',
            model=model_config,
            instruction=""" You are a back-end server that need to return a structured list.
            Return a shopping list in the defined template format based on {leftover_list} and {recipe} to tell the user what are the missing ingredients.
            Basic condiments such as salt, pepper and olive oil MUST NOT be included""",
            output_key="shopping_list",
            output_schema=ShoppingList
        )

        recipe_parser_agent = Agent(
            name='RecipeParser',
            model=model_config,
            instruction="""You are a data gathering agent that returns a JSON file of the provided output_schema
            *CRITICAL* The steps must be very accurate and complete, containing Micro and Macro nutrients.
            Steps: 
            
            1. Gather the name of the dish and the recipe steps in {recipe}
            2. you MUST return the output as a JSON with the provided template""",
            #3. you MUST use the nutrition_calc_agent to generate python code that compute the total of macro and micro nutrients and the daily percentage. 
            #DO NOT calculate totals yourself.""",
            
            output_key="recipe_step",
            output_schema=RecipeDetails
        )

        nutrition_calc_agent = Agent(
            name='NutritionCalculator',
            model=model_config,
            instruction="""You are a Python Data Analyst. 
            1. Analyze the raw nutrient data provided by the previous agent.
            2. Write and execute a Python script to calculate the total nutrients of the meal vs the daily needs.
            3. Your code MUST print the final table/result to stdout.
            4. Return the result of the code execution.""",
            code_executor=BuiltInCodeExecutor()
        )

        diet_researcher_agent = Agent(
            name='DietResearcher',
            model=model_config,
            instruction="""You are a data gathering agent that will provide raw data to a formatter agent.
            *CRITICAL* The list of the nutrients must be very accurate and complete, containing Micro and Macro nutrients.
            Steps: 
            1. Search for the macro/micro nutrients for ingredients in {recipe}, those value MUST be numbers.
            2. Search for the daily nutrient needs for an average man.""",
            #3. you MUST return the output as a JSON with the provided template""",
            #3. you MUST use the nutrition_calc_agent to generate python code that compute the total of macro and micro nutrients and the daily percentage. 
            #DO NOT calculate totals yourself.""",
            tools=[google_search, 
                   #AgentTool(agent=nutrition_calc_agent),
                   ],
            output_key="raw_diet_text",
        )

        diet_formatter_agent = Agent(
            name='DietFormatter',
            model=model_config,
            instruction="""Analyze the {raw_diet_text}.
            Calculate the totals and percentages. Every macro/micro nutrients MUST be taken into account
            Format the output strictly according to the schema.""",
            output_schema=NutritionAnalysis, # Schema is here
            output_key="nutrient_data"
        )

        diet_branch = SequentialAgent(
            name="DietBranch",
            sub_agents=[diet_researcher_agent, diet_formatter_agent]
        )

        parallel_agent = ParallelAgent(
            name="ParallelProcessing",
            sub_agents=[food_shopping_agent, diet_branch, recipe_parser_agent]
        )

        root_agent = SequentialAgent(
            name="EcoChef",
            sub_agents=[leftover_parser_agent, recipe_thinker_agent, parallel_agent]
        )
        return root_agent
    
    async def run(self, input):
        runner = InMemoryRunner(self.root_agent, plugins = [LoggingPlugin()])
        response = await runner.run_debug(f"Use this user input as a list of leftovers: {input}")
        diet_output = response[5].content.parts[0].text
        shopping_list = response[2].content.parts[0].text
        recipe_steps = response[3].content.parts[0].text
        return diet_output, shopping_list, recipe_steps
    
if __name__ == "__main__":
    chef = ChefAgent()
    # Async entry point
    diet_output, shopping_list, recipe_steps = asyncio.run(chef.run("2 eggs, half a liter of milk, old bread"))

    print("--- OUTPUT ---")
    print(diet_output)
    print(shopping_list)
    print(recipe_steps)
    
    
