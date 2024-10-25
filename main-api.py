import requests
import pandas as pd
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
import json

# Constants
API_URL = "https://api.football-data.org/v4/competitions/PL/standings"
TOTAL_TEAMS = 20

# Check if the app is running in Streamlit Cloud
if hasattr(st, "secrets") and "PL_DATA_API_KEY" in st.secrets:
    # Running in Streamlit Cloud
    API_KEY = st.secrets["PL_DATA_API_KEY"]
else:
    # Try to retrieve the API key from environment variables
    API_KEY = os.getenv('PL_DATA_API_KEY')
# Check that API key was loaded.
if not API_KEY:
   raise ValueError("API_KEY environment variable is missing")

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

# Firebase Initialization
def initialize_firebase():
    # Local path
    #cred = credentials.Certificate("C:\\IJD\\git\\pl-pool-files\\epl-prediction-tracker-firebase-adminsdk-n3wlp-3a34efb47d.json")  # Path to your service account JSON key
    
    # Check if running in Streamlit Cloud
    if hasattr(st, "secrets") and "FIREBASE_SERVICE_ACCOUNT" in st.secrets:
        firebase_credentials = json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
    else:
        # Running locally or in GitHub Actions
        firebase_credentials = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT'))

    # Check that Firebase credentials were loaded.
    if not firebase_credentials:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT environment variable is missing")

    # Initialize Firebase with the credentials
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    return db

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

    # Increase the index by 1 to have it match the first position in the table.
    epl_table.index = epl_table.index + 1
    return epl_table


# Function to score predictions against the actual standings and update predictions_df with scores
# Function also to store in Firestore
def score_predictions_and_store(db, epl_table, predictions_df):
    """
    Scores predictions based on their position relative to the actual EPL table.
    Arguments:
    - epl_table: DataFrame containing the actual EPL standings
    - predictions_df: DataFrame containing the predicted standings

    Returns:
    - scores_df: DataFrame containing the total scores for each prediction
    - predictions_df: Updated with the score for each predicted position
    """
    scores = {col: 0 for col in predictions_df.columns}
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Add a new column for storing scores in the predictions DataFrame
    for col in predictions_df.columns:
        predictions_df[f'{col}_Score'] = 0

    # Reorder columns alphabetically
    predictions_df = predictions_df[sorted(predictions_df.columns)]

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
        if '_Score' not in col:  # Ignore score columns
            for idx, predicted_team in predictions_df[col].items():
                if predicted_team in epl_table['Team'].values:
                    actual_pos = epl_table[epl_table['Team'] == predicted_team].index[0]
                    predicted_pos = idx  # The index in predictions_df is the predicted position
                    score = score_prediction(predicted_pos, actual_pos)
                    predictions_df.at[idx, f'{col}_Score'] = score  # Store score for each prediction
                    scores[col] += score  # Add to total score for this prediction

    # Create Prediction Score dataframe and add logos
    scores_df = pd.DataFrame(list(scores.items()), columns=['Prediction', 'Score'])
    scores_df['Logo'] = scores_df['Prediction'].map(LOGO_URLS)
    
    # Store the scores in Firestore
    doc_ref = db.collection("prediction_scores").document(current_time)
    doc_ref.set(scores)

    # Sort the dataframe by Score
    scores_df = scores_df.sort_values(by=['Score'], ascending=False)
    
    # Reset the dataframe index and start the index at 1
    scores_df.reset_index(drop=True, inplace=True)
    scores_df.index = scores_df.index + 1

    return scores_df, predictions_df

# Function to load historical scores from Firestore
def load_historical_scores(db):
    """Fetches all prediction scores from Firestore."""
    scores_ref = db.collection("prediction_scores")
    docs = scores_ref.stream()
    all_scores = []
    for doc in docs:
        score_data = doc.to_dict()
        score_data['Date'] = doc.id  # Use the document ID (timestamp) as the Date
        all_scores.append(score_data)
    
    if all_scores:
        return pd.DataFrame(all_scores)
    else:
        return pd.DataFrame()  # Return empty DataFrame if no scores found

# Function to display the data on a Streamlit dashboard
def display_dashboard(epl_table, scores_df, predictions_df, historical_scores):
    """Displays the prediction scores, prediction details, 
    and EPL table on a Streamlit dashboard using tabs."""
    
    # Create tabs for the different sections of the dashboard
    tab1, tab2, tab3, tab4 = st.tabs(["Prediction Scores", "Prediction Details", "EPL Table", "Score History"])

    with tab1:
        st.title("Diamond Dawg Prediction Pool")
        for i, row in scores_df.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])  # Define the widths of the columns
            col1.write(f"**{row['Prediction']}**")
            col2.write(f"{row['Score']} points")
            col3.image(row['Logo'], width=50)

    with tab2:
        st.title("Prediction Details")
        st.dataframe(predictions_df)  # Display predictions_df with scores

    with tab3:
        st.title("Latest EPL Table")
        st.dataframe(epl_table)

    with tab4:
        st.title("Scores Over Time")
        if not historical_scores.empty:
            try:
                # Set the 'Date' column as the index for plotting
                historical_scores.set_index('Date', inplace=True)
                
                # Ensure the DataFrame has valid numeric data to plot
                if historical_scores.select_dtypes(include=['number']).empty:
                    st.error("No valid score data to display in the chart.")
                else:
                    # Plot the chart with all prediction columns over time
                    st.line_chart(historical_scores)
            except KeyError as e:
                st.error(f"An error occurred: {e}")
        else:
            st.write("No historical data available.")

# Main execution
if __name__ == "__main__":
    try:
        # Initialize Firebase
        db = initialize_firebase()

        # Load the predictions CSV (add your file path if running locally)
        predictions_df = pd.read_csv("predictions.csv")
        predictions_df = predictions_df.set_index('Index')

        # Fetch the EPL standings
        epl_table = fetch_epl_standings()

        # Score the predictions and update the predictions DataFrame with individual scores
        # Also store the scores in Firestone
        scores_df, updated_predictions_df = score_predictions_and_store(db, epl_table, predictions_df)
        print(scores_df)
        print(updated_predictions_df)

        # Load historical scores from Firestore
        historical_scores = load_historical_scores(db)

        # Display the dashboard
        display_dashboard(epl_table, scores_df, updated_predictions_df, historical_scores)

    except Exception as e:
        st.error(f"An error occurred: {e}")
