# EcoChef
The problem I want to solve is the food waste on the daily basis and try to improve persons in a precarious situation meal planning. The most useful case is for me people that live alone that has leftovers in their fridge and a tiny budget.

For me it's an important problem to solve because I saw my friends living by themselves during their studies sometimes struggle to eat various meal or throwing away food that is passed. Furthermore, reducing food waste allows to improve our ecological print and even feed homeless people.

On the other side, a lot of people are eating wrong. This app allows to have a healthy diet for everyone without wasting anything.
## Pre-requesits

Create a python VENV and use the `pip install -r requirements.txt` to install the package we need for this app.

Create a .env file and add an entry 

`GOOGLE_API_KEY = 'Your Google AI API key'`

Then you can execute `python app.py` to launch the app in local.

## Architecture

We have an agent that will reshape the leftovers input into a list that is more understandable

Second agent will use google search tool to find a recipe that includes our leftovers and minimize the amount of shopping needed.

After that we'll have 3 pipelines: one to construct the leftovers list, one to decompose the steps and one that will look up for nutrients that are in the meal and the daily need for an average man. We will recover each of the output in a defined format to display the information correctly on the front-end.

![Agent Architecture](./images/app_architecure.png)