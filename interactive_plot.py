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
    
    # Set up the figure with RTL formatting (no direction property)
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'family': 'Arial Hebrew, Arial, sans-serif', 'size': 20}
        },
        # Hide axes completely
        xaxis={'visible': False, 'showticklabels': False},
        yaxis={'visible': False, 'showticklabels': False},
        # Add clear message in the center
        annotations=[{
            'text': message,
            'showarrow': False,
            'xref': "paper",
            'yref': "paper",
            'x': 0.5,
            'y': 0.5,
            'align': 'center',
            'font': {
                'family': 'Arial Hebrew, Arial, sans-serif',
                'size': 16,
                'color': color
            }
        }],
        margin={'t': 80, 'b': 20, 'l': 20, 'r': 20},
        paper_bgcolor='rgba(245,245,245,0.9)',
        plot_bgcolor='rgba(245,245,245,0.9)',
        height=300
    )
    
    return fig

# Replace all error message generation with this new approach:

def create_rtl_error_message(title, color="red", additional_text=None):
    """Create a standardized RTL error message that will display properly in Hebrew"""
    
    # Add RTL mark character to start of strings to force RTL rendering
    rtl_title = f"\u200F{title}"
    
    # Create a minimal figure with just an annotation in the center
    fig = go.Figure()
    fig.add_annotation(
        text=f"<b>{rtl_title}</b>",
        x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False,
        font=dict(
            family="Arial Hebrew, Arial, sans-serif",
            size=20,
            color=color
        ),
        align="right"  # Right align for RTL text
    )
    
    # Configure the layout for clean appearance
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis={'visible': False, 'showticklabels': False},
        yaxis={'visible': False, 'showticklabels': False},
        margin=dict(l=0, r=0, t=0, b=0),
        height=300,
        template="plotly_white"
    )
    
    # Create the message div with strongest possible RTL enforcement
    additional_text_with_rtl = []
    if additional_text:
        additional_text_with_rtl = [f"\u200F{text}" for text in additional_text]
        message_div = html.Div(
            [
                html.H3(rtl_title, 
                       style={"color": color, "textAlign": "right"}, 
                       dir="rtl"),
                *[html.P(text, 
                         style={"textAlign": "right"}, 
                         dir="rtl") for text in additional_text_with_rtl]
            ],
            style={
                "direction": "rtl", 
                "unicode-bidi": "bidi-override", 
                "text-align": "right"
            },
            dir="rtl"  # HTML dir attribute for strongest RTL support
        )
    else:
        message_div = html.Div(
            html.H3(rtl_title, 
                   style={"color": color, "textAlign": "right"}, 
                   dir="rtl"),
            style={
                "direction": "rtl", 
                "unicode-bidi": "bidi-override", 
                "text-align": "right"
            },
            dir="rtl"  # HTML dir attribute for strongest RTL support
        )
    
    return fig, message_div

# First, let's completely rewrite the Hebrew number formatter to ensure it works properly:

def format_hebrew_number(num):
    """Format numbers in Hebrew style with proper אלף/מיליון suffixes"""
    if pd.isna(num) or num == 0:
        return "0 ₪"
    
    abs_num = abs(num)
    sign = '-' if num < 0 else ''
    
    # Only use מיליון if value is at least 1 million
    if abs_num >= 1_000_000:
        # Format as millions (מיליון)
        value = abs_num / 1_000_000
        # Only show in millions if it's at least 1 million
        return f"{sign}{value:.1f} מיליון ₪".replace('.0 ', ' ')
    elif abs_num >= 1_000:
        # Format as thousands (אלף)
        value = abs_num / 1_000
        return f"{sign}{value:.1f} אלף ₪".replace('.0 ', ' ')
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
        # Load apartment and rent data
        df_preprocessed = load_apartment_data(apartment_region, apartment_rooms)
        rent_df = load_rent_data(apartment_region, apartment_rooms)
        
        # Check available years
        apartment_years = sorted(df_preprocessed['Year'].unique()) if 'Year' in df_preprocessed.columns else []
        rent_years = sorted(rent_df['שנה'].unique()) if 'שנה' in rent_df.columns else []
        
        # Find overlapping years
        available_years_for_selection = []
        if apartment_years and rent_years:
            apartment_years_set = set(apartment_years)
            rent_years_set = set(rent_years)
            available_years_for_selection = sorted(apartment_years_set.intersection(rent_years_set))
        
        # Handle no data case
        if len(available_years_for_selection) == 0:
            error_title = f'אין נתונים מלאים עבור {apartment_region} עם {apartment_rooms} חדרים'
            additional_text = []
            
            if apartment_years:
                apt_years_msg = f"טווח נתוני מחירי דירות: {min(apartment_years)} - {max(apartment_years)}"
                additional_text.append(apt_years_msg)
            else:
                additional_text.append("אין נתוני מחירי דירות")
                
            if rent_years:
                rent_years_msg = f"טווח נתוני שכירות: {min(rent_years)} - {max(rent_years)}"
                additional_text.append(rent_years_msg)
            else:
                additional_text.append("אין נתוני שכירות")
            
            error_fig, error_message = create_rtl_error_message(error_title, "red", additional_text)
            return error_fig, error_message
        
        # Now we have overlapping years, so check if start_year is in range
        earliest_year = min(available_years_for_selection)
        latest_year = max(available_years_for_selection)
        
        # Fix the year range error display:
        if start_year > latest_year or start_year < earliest_year:
            error_title = f'אזור זה זמין רק בין השנים {earliest_year} ו-{latest_year}'
            error_fig, error_message = create_rtl_error_message(error_title, "orange")
            return error_fig, error_message
        
        # Filter data to only include years from start_year onwards
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
        
        # Load all necessary data for calculations
        interest_row = load_interest_rates()
        df_cpi = load_cpi_data()
        stock_returns = load_stock_returns()
        bond_returns = load_bond_returns()
        
        # Calculate inflation factors
        inflation_factors = calculate_inflation_factors(df_cpi, start_year)
        
        # Get interest rate based on loan term
        interest_rate = get_interest_rate(interest_row, loan_term_years)
        
        # Get initial property price
        initial_price = df_preprocessed.loc[df_preprocessed['Year'].idxmin(), 'Price']
        
        # Calculate apartment investment metrics - THIS GIVES US THE DETAILED DATA
        df_apartment = calculate_investment_metrics(
            df_preprocessed, start_year, initial_price, 
            interest_rate, loan_term_years, rent_df, 
            apartment_region, apartment_rooms, inflation_factors
        )
        
        # Calculate market portfolio performance - THIS GIVES US THE DETAILED DATA 
        df_market = calculate_portfolio_performance(
            df_preprocessed, start_year, initial_price, 
            interest_rate, loan_term_years, stock_returns, 
            bond_returns, sp500_allocation, inflation_factors
        )
        
        # --------- SIMPLIFIED GRAPH APPROACH STARTS HERE ---------
        
        # Get most basic apartment data for plotting - DIRECT CALCULATIONS
        df_apt_basic = df_apartment[['Year', 'Price', 'Balance', 'Cumulative_Payments', 'Cumulative_Rent']].copy()
        # Simple, direct calculation of return: Value - Mortgage Balance - Payments + Rent Income
        df_apt_basic['Net_Worth'] = df_apt_basic['Price'] - df_apt_basic['Balance']
        df_apt_basic['Investment_Return'] = df_apt_basic['Net_Worth'] - df_apt_basic['Cumulative_Payments'] + df_apt_basic['Cumulative_Rent']
        df_apt_basic['Investment_Type'] = 'דירה'

        # Get most basic market data for plotting - DIRECT CALCULATIONS
        df_market_basic = df_market[['Year', 'Portfolio_Value', 'Cumulative_Investment']].copy()
        # Simple, direct calculation of return: Portfolio Value - Total Investment
        df_market_basic['Investment_Return'] = df_market_basic['Portfolio_Value'] - df_market_basic['Cumulative_Investment']
        df_market_basic['Investment_Type'] = 'תיק השקעות'

        # Combine for plotting
        combined_df = pd.concat([df_apt_basic, df_market_basic], ignore_index=True)
        
        # Calculate scale for y-axis with directly calculated values
        max_value = combined_df['Investment_Return'].max()
        min_value = combined_df['Investment_Return'].min()
        
        # Scale determination based on calculated values
        if max_value >= 1_000_000:
            scale = 1_000_000
            suffix = 'מיליון'
        elif max_value >= 1_000:
            scale = 1_000
            suffix = 'אלף'
        else:
            scale = 1
            suffix = ''
        
        # Create scaled version for display
        scaled_df = combined_df.copy()
        if scale > 1:
            scaled_df['Investment_Return'] = scaled_df['Investment_Return'] / scale
        
        # Create basic figure
        fig = go.Figure()
        
        # Apartment trace with detailed hover data
        apartment_data = scaled_df[scaled_df['Investment_Type'] == 'דירה']
        apartment_customdata = []
        for year in apartment_data['Year']:
            apt_row = df_apartment[df_apartment['Year'] == year].iloc[0]
            apt_basic = df_apt_basic[df_apt_basic['Year'] == year].iloc[0]
            
            apartment_customdata.append({
                'תשואה': format_hebrew_number(apt_basic['Investment_Return']),
                'שווי_הדירה': format_hebrew_number(apt_row['Price']),
                'יתרת_משכנתא': format_hebrew_number(apt_row['Balance']),
                'הכנסות_שכירות_שנתיות': format_hebrew_number(apt_row['Yearly_Rent']),
                'סהכ_הכנסות_שכירות': format_hebrew_number(apt_row['Cumulative_Rent']),
                'שכד_חודשי': format_hebrew_number(apt_row['Yearly_Rent'] / 12)
            })

        fig.add_trace(go.Scatter(
            x=apartment_data['Year'],
            y=apartment_data['Investment_Return'],
            name='דירה',
            line=dict(color='#1f77b4'),
            customdata=apartment_customdata,
            hovertemplate=
                "<b>דירה</b><br><br>" +
                "<b>פרטים כלליים:</b><br>" +
                "שנה: %{x}<br>" +
                "תשואה כוללת: %{customdata.תשואה}<br><br>" +
                "<b>פרטים נוספים:</b><br>" +
                "שווי הדירה: %{customdata.שווי_הדירה}<br>" +
                "יתרת משכנתא: %{customdata.יתרת_משכנתא}<br>" +
                "שכ\"ד חודשי: %{customdata.שכד_חודשי}<br>" +
                "הכנסות שכירות שנתיות: %{customdata.הכנסות_שכירות_שנתיות}<br>" +
                "סה\"כ הכנסות שכירות: %{customdata.סהכ_הכנסות_שכירות}<br>" +
                "<extra></extra>"
        ))

        # Market portfolio trace with detailed hover data
        market_data = scaled_df[scaled_df['Investment_Type'] == 'תיק השקעות']
        market_customdata = []
        for year in market_data['Year']:
            market_row = df_market[df_market['Year'] == year].iloc[0]
            mkt_basic = df_market_basic[df_market_basic['Year'] == year].iloc[0]
            
            # Calculate values directly to avoid column reference issues
            portfolio_value = market_row['Portfolio_Value']
            cumulative_investment = market_row['Cumulative_Investment']
            net_profit = portfolio_value - cumulative_investment
            tax = market_row.get('Tax', 0)
            total_fees = market_row.get('Total_Fees', 0)
            
            market_customdata.append({
                'תשואה_נטו': format_hebrew_number(net_profit),
                'שווי_תיק_השקעות': format_hebrew_number(portfolio_value),
                'השקעה_מצטברת': format_hebrew_number(cumulative_investment),
                'רווח_ברוטו': format_hebrew_number(net_profit + tax),
                'מס': format_hebrew_number(tax),
                'סהכ_עמלות': format_hebrew_number(total_fees),
                'אחוז_השקעה_במניות': f"{sp500_allocation}%"
            })

        fig.add_trace(go.Scatter(
            x=market_data['Year'],
            y=market_data['Investment_Return'],
            name='תיק השקעות',
            line=dict(color='#ff7f0e'),
            customdata=market_customdata,
            hovertemplate=
                "<b>תיק השקעות</b><br><br>" +
                "<b>פרטים כלליים:</b><br>" +
                "שנה: %{x}<br>" +
                "תשואה נטו: %{customdata.תשואה_נטו}<br><br>" +
                "<b>פרטים נוספים:</b><br>" +
                "שווי תיק השקעות: %{customdata.שווי_תיק_השקעות}<br>" +
                "סה\"כ השקעה: %{customdata.השקעה_מצטברת}<br>" +
                "רווח ברוטו: %{customdata.רווח_ברוטו}<br>" +
                "מס: %{customdata.מס}<br>" +
                "עמלות: %{customdata.סהכ_עמלות}<br>" +
                "אחוז השקעה במניות: %{customdata.אחוז_השקעה_במניות}<br>" +
                "<extra></extra>"
        ))
        
        # Calculate y-axis range for proper display
        y_min = min(0, scaled_df['Investment_Return'].min())
        y_max = scaled_df['Investment_Return'].max() * 1.1  # Add 10% padding
        
        # Update figure layout
        fig.update_layout(
            title='תשואה על השקעה',
            xaxis=dict(
                title='שנה',
                fixedrange=True,
                type='category'
            ),
            yaxis=dict(
                title=f'תשואה על השקעה ({suffix} ₪)',
                range=[y_min, y_max],
                fixedrange=True,
                tickformat=",.1f"
            ),
            hovermode='closest',
            dragmode=False,
            font=dict(family="Arial Hebrew, Arial, sans-serif"),
            legend=dict(title='סוג השקעה')
        )
        
        # Generate results info using directly calculated values
        latest_year = max(df_apartment['Year'])
        apt_final_year = df_apt_basic[df_apt_basic['Year'] == latest_year]
        apt_final_return = apt_final_year['Investment_Return'].values[0]

        # Get market final return directly
        market_final_year = df_market_basic[df_market_basic['Year'] == latest_year]
        market_final_return = market_final_year['Investment_Return'].values[0]

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
                    html.Strong("ריבית: "), f"{interest_rate*100:.0f}%"
                ], style={'display': 'inline-block', 'marginLeft': '2%', 'width': '30%'}),
                
                html.Div([
                    html.Strong("שנת התחלה: "), f"{start_year}"
                ], style={'display': 'inline-block', 'width': '30%'})
            ]),
            
            html.Div([
                html.Div([
                    html.Strong("רווח נטו דירה: "), format_hebrew_number(apt_final_return)
                ], style={'display': 'inline-block', 'marginLeft': '2%', 'width': '30%'}),
                
                html.Div([
                    html.Strong("רווח נטו שוק ההון: "), format_hebrew_number(market_final_return)
                ], style={'display': 'inline-block', 'marginLeft': '2%', 'width': '30%'}),
                
                html.Div([
                    html.Strong("השקעה עדיפה: "), 
                    html.Span(winner, style={'color': 'green', 'fontWeight': 'bold'})
                ], style={'display': 'inline-block', 'width': '30%'})
            ]),
        ])
        
        return fig, results_info
        
    except Exception as e:
        print(f"Error updating graph: {e}")  # Log the error for debugging
        error_title = 'שגיאה בהצגת הנתונים'
        error_fig, error_message = create_rtl_error_message(error_title, "red")
        return error_fig, error_message

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)