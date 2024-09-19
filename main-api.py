import requests
import pandas as pd
import streamlit as st

# API endpoint
url = "https://api.football-data.org/v4/competitions/PL/standings"

# Your API key (you need to sign up and get one)
headers = {'X-Auth-Token': '9dda26884d784e408cd03c8ba42dce43'}

# Send a GET request to the API
response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()
    standings = data['standings'][0]['table']
    
    # Extract relevant information
    teams = []
    played = []
    won = []
    drawn = []
    lost = []
    gf = []
    ga = []
    gd = []
    points = []

    for team in standings:
        teams.append(team['team']['name'])
        played.append(team['playedGames'])
        won.append(team['won'])
        drawn.append(team['draw'])
        lost.append(team['lost'])
        gf.append(team['goalsFor'])
        ga.append(team['goalsAgainst'])
        gd.append(team['goalDifference'])
        points.append(team['points'])

    # Create a DataFrame
    epl_table = pd.DataFrame({
        'Team': teams,
        'Played': played,
        'Won': won,
        'Drawn': drawn,
        'Lost': lost,
        'GF': gf,
        'GA': ga,
        'GD': gd,
        'Points': points
    })

    # Display the DataFrame
    print(epl_table)
else:
    print(f"Failed to retrieve data. Status code: {response.status_code}")

# Streamlit dashboard
st.title("English Premier League Table")
st.write("This is the latest EPL table:")
st.dataframe(epl_table)
