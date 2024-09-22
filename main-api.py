import requests
import pandas as pd
import streamlit as st
import os

# Constants
API_URL = "https://api.football-data.org/v4/competitions/PL/standings"
TOTAL_TEAMS = 20

# Load the API key from an environment variable for security
API_KEY = os.getenv('PL_DATA_API_KEY', 'your-default-api-key-here')

# Headers for API request
HEADERS = {'X-Auth-Token': API_KEY}

# Dictionary mapping team names to logo URLs (you can replace these with actual URLs or paths)
LOGO_URLS = {
    'IncogNeto': 'https://upload.wikimedia.org/wikipedia/en/c/cc/Chelsea_FC.svg',  # Chelsea FC
    'Sonny\'s Soldiers': 'https://upload.wikimedia.org/wikipedia/en/b/b4/Tottenham_Hotspur.svg',  # Tottenham Hotspur FC
    'Vardy Party': 'https://upload.wikimedia.org/wikipedia/hif/a/ab/Leicester_City_crest.png',  # Leicester City FC
    'Wolf Cola': 'https://upload.wikimedia.org/wikipedia/en/f/fc/Wolverhampton_Wanderers.svg',  # Wolverhampton Wanderers FC
    'Championship Playoff Champions': 'https://upload.wikimedia.org/wikipedia/en/c/c9/FC_Southampton.svg'  # Southampton FC
}

# Function to call the API and retrieve EPL standings
def fetch_epl_standings():
    """Fetches the current EPL standings from the Football-Data.org API."""
    response = requests.get(API_URL, headers=HEADERS)

    if response.status_code != 200:
        raise Exception(f"Failed to retrieve data. Status code: {response.status_code}")
    
    data = response.json()
    standings = data['standings'][0]['table']

    # Create a DataFrame from the standings data
    epl_table = pd.DataFrame({
        'Team': [team['team']['name'] for team in standings],
        'Played': [team['playedGames'] for team in standings],
        'Won': [team['won'] for team in standings],
        'Drawn': [team['draw'] for team in standings],
        'Lost': [team['lost'] for team in standings],
        'GF': [team['goalsFor'] for team in standings],
        'GA': [team['goalsAgainst'] for team in standings],
        'GD': [team['goalDifference'] for team in standings],
        'Points': [team['points'] for team in standings]
    })

    epl_table['Position'] = epl_table.index + 1  # Assign position based on index
    return epl_table


# Function to score predictions against the actual standings
def score_predictions(epl_table, predictions_df):
    """
    Scores predictions based on their position relative to the actual EPL table.
    Arguments:
    - epl_table: DataFrame containing the actual EPL standings
    - predictions_df: DataFrame containing the predicted standings

    Returns:
    - scores_df: DataFrame containing the scores for each prediction
    """
    scores = {col: 0 for col in predictions_df.columns}

    def score_prediction(predicted_pos, actual_pos):
        """Applies the scoring rules to a prediction."""
        if predicted_pos == actual_pos:
            return 10
        elif abs(predicted_pos - actual_pos) <= 3:
            return 5
        elif abs(predicted_pos - actual_pos) <= 5:
            return 2
        elif (predicted_pos <= TOTAL_TEAMS / 2 and actual_pos <= TOTAL_TEAMS / 2) or (
            predicted_pos > TOTAL_TEAMS / 2 and actual_pos > TOTAL_TEAMS / 2):
            return 1
        return 0

    # Score each prediction for each team
    for col in predictions_df.columns:
        for idx, predicted_team in predictions_df[col].items():
            if predicted_team in epl_table['Team'].values:
                actual_pos = epl_table[epl_table['Team'] == predicted_team]['Position'].values[0]
                predicted_pos = idx  # The index in predictions_df is the predicted position
                scores[col] += score_prediction(predicted_pos, actual_pos)

    # Create Prediction Score dataframe
    df = pd.DataFrame(list(scores.items()), columns=['Prediction', 'Score'])
    df['Logo'] = df['Prediction'].map(LOGO_URLS)
    
    # Sort the datafram by Score
    df = df.sort_values(by=['Score'], ascending=False)
    
    # Reset the dataframe index and start the index at 1
    df.reset_index(drop=True, inplace=True)
    df.index = df.index + 1

    return df


# Function to display the data on a Streamlit dashboard
def display_dashboard(epl_table, scores_df):
    """Displays the EPL table and prediction scores on a Streamlit dashboard."""
    #st.title("English Premier League Table")
    #st.write("This is the latest EPL table:")
    #st.dataframe(epl_table)

    st.title("Diamond Dawg Prediction Pool")
    for i, row in scores_df.iterrows():
        col1, col2 = st.columns([1, 4])
        col1.image(row['Logo'], width=50)  # Display logo
        col2.write(f"**{row['Prediction']}**: {row['Score']} points")


# Main execution
if __name__ == "__main__":
    try:
        # Load the predictions CSV (add your file path if running locally)
        predictions_df = pd.read_csv("predictions.csv")
        predictions_df = predictions_df.set_index('Index')

        # Fetch the EPL standings
        epl_table = fetch_epl_standings()

        # Score the predictions
        scores_df = score_predictions(epl_table, predictions_df)

        # Display the results in the Streamlit app
        display_dashboard(epl_table, scores_df)

    except Exception as e:
        st.error(f"An error occurred: {e}")
