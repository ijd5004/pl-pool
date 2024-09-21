import requests
import pandas as pd
import streamlit as st

# API endpoint
url = "https://api.football-data.org/v4/competitions/PL/standings"

# Your API key (you need to sign up and get one)
headers = {'X-Auth-Token': '9dda26884d784e408cd03c8ba42dce43'}

# Read in PL table predictions
predictions_df = pd.read_csv('predictions.csv')

# Clean the predictions dataframe (use 'Index' as the index for easier comparison)
predictions_df = predictions_df.set_index('Index')

# Initialize a dictionary to store the scores for each prediction column
scores = {col: 0 for col in predictions_df.columns}

# Define the total number of teams in the EPL (typically 20)
total_teams = 20


# Scoring function that takes in predicted and actual positions and returns a score based on the rules
def score_prediction(predicted_pos, actual_pos):
    if predicted_pos == actual_pos:
        return 10  # Exact match
    elif abs(predicted_pos - actual_pos) <= 3:
        return 5  # Within 3 positions
    elif abs(predicted_pos - actual_pos) <= 5:
        return 2  # Within 5 positions
    elif (predicted_pos <= total_teams / 2 and actual_pos <= total_teams / 2) or (
        predicted_pos > total_teams / 2 and actual_pos > total_teams / 2):
        return 1  # In the correct half of the table
    return 0  # No points if none of the conditions are met

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
    epl_table_df = pd.DataFrame({
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
    print(epl_table_df)
    #epl_table.to_csv('sample_epl_table.csv')

    # Clean up the EPL table, keeping only the relevant columns (Team name and Position)
    epl_table_df = epl_table_df[['Team']]  # Keep only the team names
    epl_table_df['Position'] = epl_table_df.index + 1  # Add a Position column (since index starts from 0)

    # Score each prediction for every team
    for col in predictions_df.columns:
        for idx, predicted_team in predictions_df[col].items():
            if predicted_team in epl_table_df['Team'].values:
                actual_pos = epl_table_df[epl_table_df['Team'] == predicted_team]['Position'].values[0]
                predicted_pos = idx  # The index in predictions_df is the predicted position
                scores[col] += score_prediction(predicted_pos, actual_pos)

    # Convert the scores to a DataFrame for easier viewing; sort by Score
    scores_df = pd.DataFrame(list(scores.items()), columns=['Prediction', 'Score']).sort_values(by=['Score'], ascending=False)
    print(scores_df)
    
    # Streamlit dashboard
    st.title("Diamond Dawgs PL Predction")
    st.dataframe(scores_df)
else:
    print(f"Failed to retrieve data. Status code: {response.status_code}")
