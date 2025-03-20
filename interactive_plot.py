import pandas as pd
import plotly.express as px
import numpy as np
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

# Import all your existing functions from plot.py
from plot import (load_apartment_data, load_rent_data, load_interest_rates, load_cpi_data,
                 load_stock_returns, load_bond_returns, get_interest_rate, calculate_mortgage_payment,
                 remaining_balance, get_monthly_rent, calculate_cumulative_rent, calculate_inflation_factors,
                 calculate_investment_metrics, calculate_portfolio_performance)

# Add this helper function at the beginning of your file, after imports

def create_rtl_error_figure(title, message, color="red"):
    """Create a properly formatted RTL figure for error messages in Hebrew."""
    fig = go.Figure()
    
    # Set up the figure with RTL formatting
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'family': 'Arial Hebrew, Arial, sans-serif', 'size': 20}
        },
        xaxis={
            'visible': False
        },
        yaxis={
            'visible': False
        },
        annotations=[{
            'text': message,
            'showarrow': False,
            'xref': "paper",
            'yref': "paper",
            'x': 0.5,
            'y': 0.5,
            'font': {
                'family': 'Arial Hebrew, Arial, sans-serif',
                'size': 16,
                'color': color
            }
        }],
        margin={'t': 50, 'b': 20, 'l': 20, 'r': 20},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=300
    )
    
    return fig

# Add this function near the top of your file:

def format_hebrew_number(num):
    """Format numbers in Hebrew style with אלף and מיליון instead of K and M"""
    abs_num = abs(num)
    sign = '-' if num < 0 else ''
    
    if abs_num >= 1_000_000:
        # Format as millions (מיליון)
        return f"{sign}{abs_num / 1_000_000:.0f} מיליון ₪"
    elif abs_num >= 1_000:
        # Format as thousands (אלף)
        return f"{sign}{abs_num / 1_000:.0f} אלף ₪"
    else:
        # Format regular numbers
        return f"{sign}{abs_num:.0f} ₪"

# Initialize the Dash app with RTL support
app = dash.Dash(__name__, 
                meta_tags=[
                    {"name": "viewport", "content": "width=device-width, initial-scale=1"}
                ])

# Add CSS for RTL support
app.index_string = '''
<!DOCTYPE html>
<html dir="rtl" lang="he">
    <head>
        {%metas%}
        <title>השוואת השקעות: דירה מול תיק השקעות</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Arial Hebrew', 'Times New Roman', Arial, sans-serif;
                margin: 0;
                direction: rtl;
            }
            .dash-dropdown {
                text-align: right;
            }
            .dash-graph {
                direction: ltr;
            }
            .control-panel {
                background-color: #f8f9fa;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 15px;
            }
            .results-panel {
                margin-top: 10px;
                margin-bottom: 10px;
                max-height: 200px;
                overflow-y: auto;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Fix the data loading section to ensure 'Year' column exists

# Load data upfront to get available options for dropdowns
try:
    # Load apartment data to get available regions and room types
    df_all = pd.read_excel('preprocessed_apt_prices.xlsx', engine='openpyxl')
    available_regions = sorted(df_all['אזור'].unique())
    available_room_types = sorted(df_all['חדרים בדירה'].unique())
    
    # Make sure we have a Year column in the apartment data
    if 'Year' not in df_all.columns and 'שנה' in df_all.columns:
        df_all['Year'] = df_all['שנה']
    
    # Load CPI data to get available years
    df_cpi = load_cpi_data()
    
    # Pre-load other datasets
    interest_row = load_interest_rates()
    stock_returns = load_stock_returns()
    bond_returns = load_bond_returns()
    
    # Find the overlapping years where all datasets have data
    apartment_years = set(df_all['Year'].unique())
    cpi_years = set(df_cpi['Year'].unique())
    stock_years = set(stock_returns.index)
    bond_years = set(bond_returns.index)
    
    # Find the intersection of all year sets
    common_years = apartment_years.intersection(cpi_years, stock_years, bond_years)
    available_years = sorted(common_years)
    
    if not available_years:
        print("Warning: No common years found across all datasets!")
        # Fallback to using years from CPI data
        available_years = sorted(cpi_years)
    
    # Set a reasonable default year that's within the available range
    default_year = min(available_years) if available_years else 1995
    
    print(f"Available years for analysis: {min(available_years)} to {max(available_years)}")
    
except Exception as e:
    print(f"Error loading initial data: {e}")
    import traceback
    traceback.print_exc()  # Print the full traceback for better debugging
    exit(1)

# Set up the app layout
app.layout = html.Div([
    html.H1("השוואת השקעה: דירה מול שוק ההון", style={'textAlign': 'center'}),
    
    # More compact control panel
    html.Div([
        html.Div([
            # First row with dropdowns
            html.Div([
                html.Div([
                    html.Label("אזור"),
                    dcc.Dropdown(
                        id='region-dropdown',
                        options=[{'label': region, 'value': region} for region in available_regions],
                        value='כולם',
                        clearable=False
                    ),
                ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '1%'}),
                
                html.Div([
                    html.Label("חדרים"),
                    dcc.Dropdown(
                        id='rooms-dropdown',
                        options=[{'label': room, 'value': room} for room in available_room_types],
                        value='הכל',
                        clearable=False
                    ),
                ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '1%'}),
                
                html.Div([
                    html.Label("שנת התחלה"),
                    dcc.Dropdown(
                        id='start-year-dropdown',
                        options=[{'label': str(year), 'value': year} for year in available_years],
                        value=1994,
                        clearable=False
                    ),
                ], style={'width': '32%', 'display': 'inline-block'}),
            ], style={'marginBottom': '10px'}),
            
            # Second row with sliders
            html.Div([
                html.Div([
                    html.Label("תקופת המשכנתא (שנים)"),
                    dcc.Slider(
                        id='loan-term-slider',
                        min=5,
                        max=30,
                        step=5,
                        marks={i: str(i) for i in range(5, 31, 5)},
                        value=25
                    ),
                ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '2%'}),
                
                html.Div([
                    html.Label("אחוז השקעה במניות S&P 500"),
                    # Move bond allocation text above the slider
                    html.Div([
                        html.Span("אחוז השקעה באג\"ח: "),
                        html.Span(id='bond-allocation')
                    ], style={'fontSize': 'smaller', 'textAlign': 'center', 'marginBottom': '5px'}),
                    dcc.Slider(
                        id='sp500-slider',
                        min=0,
                        max=100,
                        step=10,
                        marks={i: str(i) for i in range(0, 101, 20)},
                        value=80
                    ),
                ], style={'width': '48%', 'display': 'inline-block'}),
            ]),
        ], className='control-panel'),
                
        # Result information in a compact format
        html.Div(id='results-info', className='results-panel'),
        
        # Graph takes most of the space
        html.Div([
            dcc.Graph(
                id='investment-comparison-graph',
                style={'height': '70vh'}  # Make the graph take 70% of viewport height
            )
        ], style={'marginTop': '10px'}),
        
        # Footer
        html.Div(
            "מקורות נתונים: מחירי נדל\"ן בישראל, תשואות S&P 500, תשואות אג\"ח",
            style={'marginTop': '10px', 'fontSize': 'smaller', 'fontStyle': 'italic', 'textAlign': 'center'}
        )
    ], style={'margin': '0 auto', 'maxWidth': '1200px', 'padding': '10px'})
])

# Calculate and update bond allocation text
@app.callback(
    Output('bond-allocation', 'children'),
    [Input('sp500-slider', 'value')]
)
def update_bond_allocation(sp500_value):
    return f"{100 - sp500_value}%"

# Main callback to update the graph and results based on all inputs
@app.callback(
    [Output('investment-comparison-graph', 'figure'),
     Output('results-info', 'children')],
    [Input('region-dropdown', 'value'),
     Input('rooms-dropdown', 'value'),
     Input('loan-term-slider', 'value'),
     Input('start-year-dropdown', 'value'),
     Input('sp500-slider', 'value')]
)
def update_graph(apartment_region, apartment_rooms, loan_term_years, start_year, sp500_allocation):
    try:
        # Load BOTH apartment and rent data up front
        df_preprocessed = load_apartment_data(apartment_region, apartment_rooms)
        rent_df = load_rent_data(apartment_region, apartment_rooms)
        
        # Check available years in apartment price data
        apartment_years = sorted(df_preprocessed['Year'].unique()) if 'Year' in df_preprocessed.columns else []
        
        # Check available years in rent data
        rent_years = sorted(rent_df['שנה'].unique()) if 'שנה' in rent_df.columns else []
        
        # Find overlapping years between apartment and rent data
        if apartment_years and rent_years:
            # Convert to sets for intersection
            apt_years_set = set(apartment_years)
            rent_years_set = set(rent_years)
            available_years_for_selection = sorted(apt_years_set.intersection(rent_years_set))
        else:
            available_years_for_selection = []
        
        if len(available_years_for_selection) == 0:
            # No overlapping data for this region/room combination
            empty_fig = go.Figure()
            
            # Configure the figure for RTL support
            empty_fig.update_layout(
                title=f'אין נתונים מלאים עבור {apartment_region} עם {apartment_rooms} חדרים',
                xaxis=dict(title='שנה', autorange="reversed"),  # Reverse X-axis for RTL effect
                yaxis=dict(title='תשואה'),
                annotations=[dict(
                    text=f'אין נתוני מחיר ושכירות מלאים עבור {apartment_region} עם {apartment_rooms} חדרים',
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    font=dict(
                        family="Arial Hebrew, Arial, sans-serif",
                        size=14
                    )
                )],
                font=dict(
                    family="Arial Hebrew, Arial, sans-serif",
                ),
                direction="rtl"
            )
            
            # Provide more detailed information about what's missing
            apt_years_msg = f"טווח נתוני מחירי דירות: {min(apartment_years)} - {max(apartment_years)}" if apartment_years else "אין נתוני מחירי דירות"
            rent_years_msg = f"טווח נתוני שכירות: {min(rent_years)} - {max(rent_years)}" if rent_years else "אין נתוני שכירות"
            
            return empty_fig, html.Div([
                html.H4(f"אין נתונים מלאים עבור {apartment_region} עם {apartment_rooms} חדרים", 
                        style={'color': 'red', 'textAlign': 'center', 'direction': 'rtl'}),
                html.P(apt_years_msg, style={'textAlign': 'center', 'direction': 'rtl'}),
                html.P(rent_years_msg, style={'textAlign': 'center', 'direction': 'rtl'})
            ], style={'direction': 'rtl'})
        
        # Now we have overlapping years, so check if start_year is in range
        earliest_year = min(available_years_for_selection)
        latest_year = max(available_years_for_selection)
        
        # Check if selected start year is within available range
        if start_year > latest_year or start_year < earliest_year:
            # Create a single message with just the year range
            error_title = f'אזור זה זמין רק בין השנים {earliest_year} ו-{latest_year}'
            
            # No additional message text in the figure
            empty_fig = create_rtl_error_figure(error_title, "", "orange")
            
            # Only the heading, no additional paragraph elements
            return empty_fig, html.Div([
                html.H4(error_title, style={'color': 'orange', 'textAlign': 'center'})
            ], style={'direction': 'rtl'})
        
        # Now filter data to only include years from start_year onwards
        df_preprocessed = df_preprocessed[df_preprocessed['Year'] >= start_year]
        if len(df_preprocessed) == 0:
            # This shouldn't happen now with the checks above, but just in case
            empty_fig = go.Figure()
            empty_fig.update_layout(
                title=f'אין נתונים זמינים לשנים שנבחרו',
                xaxis=dict(title='שנה'),
                yaxis=dict(title='תשואה')
            )
            return empty_fig, html.Div([
                html.H4(f"אין מספיק נתונים להצגת התוצאות", style={'color': 'red', 'textAlign': 'center'})
            ])
        
        # Load remaining data now that we're sure we have apartment data
        rent_df = load_rent_data(apartment_region, apartment_rooms)
        
        # Rest of the function remains the same...
        
        # Calculate other parameters
        inflation_factors = calculate_inflation_factors(df_cpi, start_year)
        interest_rate = get_interest_rate(interest_row, loan_term_years)
        initial_price = df_preprocessed.loc[df_preprocessed['Year'].idxmin(), 'Price']
        
        # Calculate apartment investment metrics
        df_apartment = calculate_investment_metrics(
            df_preprocessed, start_year, initial_price, 
            interest_rate, loan_term_years, rent_df, 
            apartment_region, apartment_rooms, inflation_factors
        )
        
        # Calculate stock/bond portfolio performance
        df_market = calculate_portfolio_performance(
            df_preprocessed, start_year, initial_price, 
            interest_rate, loan_term_years, stock_returns, 
            bond_returns, sp500_allocation, inflation_factors
        )
        
        # Create plot data
        df_apt_plot = df_apartment[['Year', 'Investment_Return']].copy()
        df_apt_plot['Investment_Type'] = 'דירה'

        df_market_plot = df_market[['Year', 'Investment_Return']].copy()
        df_market_plot['Investment_Type'] = 'תיק השקעות'

        combined_df = pd.concat([df_apt_plot, df_market_plot], ignore_index=True)

        # Create the figure (LTR for graph)
        fig = px.line(
            combined_df,
            x='Year',
            y='Investment_Return',
            color='Investment_Type',
            title='תשואה ריאלית על השקעה (מותאמת לאינפלציה)',
            labels={
                'Investment_Return': 'תשואה על השקעה (₪ במונחי היום)', 
                'Year': 'שנה',
                'Investment_Type': 'סוג השקעה'  # Add Hebrew translation for Investment_Type
            }
        )

        # Update the formatter for hover text
        fig.update_traces(
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'שנה: %{x}<br>' +
                         'תשואה: %{y:.0f} ₪<extra></extra>'
        )

        fig.update_layout(
            xaxis_title='שנה',
            yaxis_title='תשואה על השקעה (₪ במונחי היום)',
            yaxis_title_standoff=30,  # Increase distance from axis
            legend_title='סוג השקעה',
            font=dict(
                family="Arial Hebrew, Arial, sans-serif",
            ),
            # Format y-axis ticks without decimals
            yaxis=dict(
                tickformat=",.0f",
            )
        )

        # Apply custom tick formatting to show Hebrew style numbers (thousands/millions)
        tickvals = fig.layout.yaxis.tickvals if fig.layout.yaxis.tickvals else []
        fig.update_layout(
            yaxis=dict(
                ticktext=[format_hebrew_number(val) for val in tickvals],
                tickvals=tickvals,
            )
        )

        # Generate compact results info with Hebrew number formatting
        latest_year = max(df_apartment['Year'])
        apt_final_return = df_apartment.loc[df_apartment['Year'] == latest_year, 'Investment_Return'].values[0]
        market_final_return = df_market.loc[df_market['Year'] == latest_year, 'Investment_Return'].values[0]

        winner = "דירה" if apt_final_return > market_final_return else "תיק השקעות"

        results_info = html.Div([
            html.Div([
                html.Div([
                    html.Strong("מחיר דירה התחלתי: "), format_hebrew_number(initial_price)
                ], style={'display': 'inline-block', 'marginLeft': '2%', 'width': '30%'}),
                
                html.Div([
                    html.Strong("הון עצמי (25%): "), format_hebrew_number(initial_price * 0.25)
                ], style={'display': 'inline-block', 'marginLeft': '2%', 'width': '30%'}),
                
                html.Div([
                    html.Strong("משכנתא (75%): "), format_hebrew_number(initial_price * 0.75)
                ], style={'display': 'inline-block', 'width': '30%'})
            ]),
            
            html.Div([
                html.Div([
                    html.Strong("תקופת משכנתא: "), f"{loan_term_years} שנים"
                ], style={'display': 'inline-block', 'marginLeft': '2%', 'width': '30%'}),
                
                html.Div([
                    html.Strong("ריבית: "), f"{interest_rate*100:.0f}%"  # Removed decimal points
                ], style={'display': 'inline-block', 'marginLeft': '2%', 'width': '30%'}),
                
                html.Div([
                    html.Strong("שנת התחלה: "), f"{start_year}"
                ], style={'display': 'inline-block', 'width': '30%'})
            ]),
            
            html.Div([
                html.Div([
                    html.Strong("תשואה סופית דירה: "), format_hebrew_number(apt_final_return)
                ], style={'display': 'inline-block', 'marginLeft': '2%', 'width': '30%'}),
                
                html.Div([
                    html.Strong("תשואה סופית שוק ההון: "), format_hebrew_number(market_final_return)
                ], style={'display': 'inline-block', 'marginLeft': '2%', 'width': '30%'}),
                
                html.Div([
                    html.Strong("השקעה עדיפה: "), 
                    html.Span(winner, style={'color': 'green', 'fontWeight': 'bold'})
                ], style={'display': 'inline-block', 'width': '30%'})
            ]),
        ])
        
        return fig, results_info
        
    except Exception as e:
        print(f"Error updating graph: {e}")
        
        error_title = 'שגיאה בהצגת הנתונים'
        error_msg = f'אירעה שגיאה: {str(e)}'
        
        empty_fig = create_rtl_error_figure(error_title, error_msg)
        
        return empty_fig, html.Div([
            html.H4("שגיאה בהצגת הנתונים", 
                   style={'color': 'red', 'textAlign': 'center'}),
            html.P(f"פרטי השגיאה: {str(e)}", 
                  style={'textAlign': 'center'})
        ], style={'direction': 'rtl'})

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)