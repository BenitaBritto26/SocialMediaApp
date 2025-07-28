# head up before you start:

# Make sure you have the gemini library installed and your API key set in the environment variable GEMINI_API_KEY.
# You can install the gemini library using pip:
# pip install google-genai
# then in the terminal, set the environment variable:
# export GEMINI_API_KEY='your_api_key_here'

# omg copilot literallt typed everything after heads up woahhh


#TO DO:
# Put API key as a seperate file

#imports the streamlit library for frontend stuff
import streamlit as st
# imports json for reading json files
import json
# imports the genai library for interacting with Gemini API
from google import genai
import os
import requests

# Load environment variables from a .env file
from dotenv import load_dotenv
load_dotenv("API_KEY.env")


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# App title
st.title("Social Media Profile Analyzer")

# User input section
# input1 = st.text_area("Enter the profile information here:", height=300)
input1 = st.file_uploader("Upload a JSON file with profile information:", type=["json"])

#Creating prompts:
prompt0 = "Between each section, put a dashed line to keep the sections separate. "
prompt1 = "Give the user a percent of how unsafe their account is (higher percentage means they are revealing more sensitive data that can be used to exploit the user)."
prompt2 = "Give a bullet point list of vulnerabilities of this social media profile."
prompt3 = "Give a 3-5 sentence summary of possible solutions that could be implemented to resolve said vulnerabilities."
prompt4 = "Give suggestions of which users this profile should be accessible to (Eg: family, close friends, mutual friends, public)."
prompt5 = "Give a 3-5 prediction summary of possible breaches to the account or threats that could result from not making any changes to the current account."

prompts = prompt0, prompt1, prompt2, prompt3, prompt4, prompt5

# verify input1 exists
if input1 is not None:
    # Read the JSON file
    data_str = input1.read().decode("utf-8")

    # Create analyze button
    if st.button("Analyze"):
        
        #Loading screen
        with st.spinner("Analyzing..."):
            
            #Calling Gemini API to generate content
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                                
                #contents=["Review the attached profile and give me a short 2-3 sentence summary of how much risk the user is of revealing personal data.", data_str]
                contents=[prompts, data_str]
            )

        #Printing gemini's response
        st.text_area("Profile feedback:", response.text, height=300)

        bottom_placeholder = st.empty()
        bottom_placeholder.success("Analysis complete!")


# REMINDER TO SELF:
# To run the app use the following script --> /usr/bin/python3 -m streamlit run Appv2.py
