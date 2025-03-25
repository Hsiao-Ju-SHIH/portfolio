from dash import dcc, Dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Updated dataset for PE LP firm with direct investments and fund holdings
data = {
    "Investment": ["AAPL (Public)", "TSLA (Public)", "IKEA (Private)", "Huawei (Private)", 
                   "Blackstone growth fund", "KKR value fund", "NVDA (Public)"],
    "Amount": [10000, 12000, 8000, 7000, 15000, 18000, 5000],  # Amounts in each investment
    "Asset Class": ["Public Equity", "Public Equity", "Private Direct", "Private Direct", 
                    "Fund", "Fund", "Public Equity"],  # Asset class of each investment
    "Risk Level": ["High", "Medium", "High", "Low", "High", "Medium", "Low"],  # Risk levels
    "Growth Rate (%)": [10, 12, 8, 6, 15, 10, 14],  # Growth rates of each investment
}

# Fund holdings data: showing percentage of each fund's investment in each asset
fund_holdings = {
    "Fund": ["Blackstone growth fund", "Blackstone growth fund", "KKR value fund", "KKR value fund", "KKR value fund"],
    "Investment": ["AAPL (Public)", "IKEA (Private)", "TSLA (Public)", "Huawei (Private)", "Public Equity 4"],
    "Holdings (%)": [0.60, 0.30, 0.50, 0.40, 0.75],  # Percentage of funds invested in each investment
}

# Convert to DataFrames
df = pd.DataFrame(data)
df_holdings = pd.DataFrame(fund_holdings)

# Function to calculate total investments including fund holdings
def calculate_total_investments(df, df_holdings):
    # Merge the direct investments with the fund holdings
    df_fund_investments = pd.merge(df_holdings, df, left_on="Investment", right_on="Investment", how="left")
    df_fund_investments['Fund Investment Amount'] = df_fund_investments['Amount'] * df_fund_investments['Holdings (%)']
    
    # Now, merge the calculated fund investment amounts with the original dataframe
    df_updated = df.copy()
    
    # Adding new investments (like Public Equity 4) to the main dataframe if not already present
    new_investments = df_fund_investments[df_fund_investments['Investment'].isnull()]
    if not new_investments.empty:
        new_investments = new_investments[['Investment', 'Fund Investment Amount']].dropna()
        # Add new investments to the original dataframe
        df_updated = pd.concat([df_updated, new_investments], ignore_index=True)

    # Add the fund investment amount to the direct investment amount for the relevant investment
    for idx, row in df_fund_investments.iterrows():
        investment = row['Investment']
        fund_investment = row['Fund Investment Amount']
        
        # If the investment already exists, add to its amount; if not, add a new row
        if investment in df_updated['Investment'].values:
            df_updated.loc[df_updated['Investment'] == investment, 'Amount'] += fund_investment
        else:
            new_row = pd.DataFrame([{
                'Investment': investment, 
                'Amount': fund_investment, 
                'Asset Class': 'Public Equity' if 'Public Equity' in investment else 'Private Direct', 
                'Risk Level': 'Unknown', 
                'Growth Rate (%)': 0
            }])

            df_updated = pd.concat([df_updated, new_row], ignore_index=True)
    
    return df_updated

# First-level pie chart for asset class mix
def asset_class_pie():
    df_asset_class = df.groupby('Asset Class').sum().reset_index()
    fig = px.pie(df_asset_class, names='Asset Class', values='Amount', hole=0.4)
    fig.update_layout(template='presentation', title='Investment Distribution by Asset Class')
    return fig

# New pie chart for updated holdings after fund investment adjustments
def updated_holdings_pie():
    df_updated = calculate_total_investments(df, df_holdings)
    fig = px.pie(df_updated, names='Investment', values='Amount', hole=0.4)
    fig.update_layout(template='presentation', title='Updated Investment Distribution (Including Fund Holdings)')
    return fig

# Creating app layout
app.layout = dbc.Container([
    dbc.Card([
        dbc.Button('🡠', id='back-button', outline=True, size="sm",
                   className='mt-2 ml-2 col-1', style={'display': 'none'}),
        dbc.Row(
            dcc.Graph(
                id='graph',
                figure=asset_class_pie()
            ), justify='center'
        ),
        dbc.Row(
            dcc.Graph(
                id='updated-graph',
                figure=updated_holdings_pie()
            ), justify='center'
        )
    ], className='mt-3')
])

# Callback
@app.callback(
    [Output('graph', 'figure'),
     Output('back-button', 'style'),
     Output('back-button', 'n_clicks')],  # Reset the button click count
    [Input('graph', 'clickData'),  # For getting the asset class name from graph
     Input('back-button', 'n_clicks')]  # For handling back button clicks
)
def drilldown(click_data, n_clicks):
    # Handle back button click
    if n_clicks is not None and n_clicks > 0:
        # Reset back button click count
        return asset_class_pie(), {'display': 'none'}, 0

    # Handle clickData (click on the pie chart)
    if click_data:
        asset_class = click_data['points'][0]['label']

        # Filter investment data by asset class
        asset_class_df = df[df['Asset Class'] == asset_class]

        # If the asset class is 'Fund', we need to merge the fund investments with the underlying investments
        if asset_class == "Fund":
            # Merge the investments from the funds with the direct investments they hold
            # Aggregating the Amounts for holdings that are also in "Fund"
            fund_investments = asset_class_df.groupby('Investment').sum().reset_index()

            # Create pie chart for selected asset class
            fig = px.pie(fund_investments, names='Investment', values='Amount', color='Risk Level',
                         title=f'<b>{asset_class} Breakdown (Including Direct Holdings)</b>', hole=0.4)
            fig.update_layout(showlegend=True, template='presentation')

            # Display back button to return to pie chart
            return fig, {'display': 'block'}, n_clicks  # Keep the back button active

        # If it's a direct investment (Public Equity or Private Direct), just show the breakdown
        fig = px.pie(asset_class_df, names='Investment', values='Amount', color='Risk Level',
                     title=f'<b>{asset_class} Breakdown</b>', hole=0.4)
        fig.update_layout(showlegend=True, template='presentation')

        # Display back button to return to pie chart
        return fig, {'display': 'block'}, n_clicks  # Keep the back button active

    # Default return to pie chart if no click or back button action
    return asset_class_pie(), {'display': 'none'}, 0  # Reset back button clicks to 0 when returning to pie chart

if __name__ == '__main__':
    app.run(debug=True)
