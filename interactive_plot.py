import pandas as pd
import numpy as np
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import logging
from functools import lru_cache
import os
from flask import Flask

# Set up proper logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import all your existing functions from plot.py
from plot import (load_apartment_data, load_rent_data, load_interest_rates, load_cpi_data,
                 load_stock_returns, load_bond_returns, get_interest_rate, calculate_inflation_factors,
                 calculate_investment_metrics, calculate_portfolio_performance)

# ---- EFFICIENCY FIX 1: CONSOLIDATE ERROR HANDLING ----
def create_rtl_message(title, color="red", additional_text=None, is_error=True):
    """
    Unified function for creating RTL error/info messages - eliminates duplicate code
    """
    rtl_title = f"\u200F{title}"
    
    # Create a minimal figure
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
        align="right"
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis={'visible': False, 'showticklabels': False},
        yaxis={'visible': False, 'showticklabels': False},
        margin=dict(l=0, r=0, t=0, b=0),
        height=300,
        template="plotly_white"
    )
    
    # Create the message div
    additional_text_with_rtl = []
    if additional_text:
        additional_text_with_rtl = [f"\u200F{text}" for text in additional_text]
    
    message_div = html.Div(
        [
            html.H3(rtl_title, style={"color": color, "textAlign": "right"}, dir="rtl"),
            *[html.P(text, style={"textAlign": "right"}, dir="rtl") for text in additional_text_with_rtl]
        ],
        style={
            "direction": "rtl", 
            "unicode-bidi": "bidi-override", 
            "text-align": "right"
        },
        dir="rtl"
    )
    
    return fig, message_div

# ---- EFFICIENCY FIX 2: MEMOIZE EXPENSIVE FORMATTING FUNCTION ----
@lru_cache(maxsize=1000)
def format_hebrew_number(num):
    """Memoized formatter for Hebrew numbers to avoid repeated calculations"""
    if pd.isna(num) or num == 0:
        return "0 ₪"
    
    abs_num = abs(num)
    sign = '-' if num < 0 else ''
    
    if abs_num >= 1_000_000:
        value = abs_num / 1_000_000
        return f"{sign}{value:.1f} מיליון ₪".replace('.0 ', ' ')
    elif abs_num >= 1_000:
        value = abs_num / 1_000
        return f"{sign}{value:.1f} אלף ₪".replace('.0 ', ' ')
    else:
        return f"{sign}{abs_num:.0f} ₪"

# ---- EFFICIENCY FIX 3: PRELOAD DATA JUST ONCE ----
# Load all data upfront to prevent redundant loading
try:
    # Load apartment data
    df_all = pd.read_excel('preprocessed_apt_prices.xlsx', engine='openpyxl')
    available_regions = sorted(df_all['אזור'].unique())
    
    # Filter out the 4-5 and 5-6 room options
    all_room_types = df_all['חדרים בדירה'].unique()
    available_room_types = sorted([room for room in all_room_types 
                                  if room not in ['4-5', '5-6']])
    
    if 'Year' not in df_all.columns and 'שנה' in df_all.columns:
        df_all['Year'] = df_all['שנה']
    
    # Load all other datasets once
    df_cpi = load_cpi_data()
    interest_rates = load_interest_rates()
    stock_returns = load_stock_returns()
    bond_returns = load_bond_returns()
    
    # Find available years once
    apartment_years = set(df_all['Year'].unique())
    cpi_years = set(df_cpi['Year'].unique())
    stock_years = set(stock_returns.index)
    bond_years = set(bond_returns.index)
    
    # Available years for all datasets
    common_years = apartment_years.intersection(cpi_years, stock_years, bond_years)
    available_years = sorted(common_years)
    
    if not available_years:
        logger.warning("No common years found across all datasets!")
        available_years = sorted(cpi_years)
    
    default_year = min(available_years) if available_years else 1995
    logger.info(f"Available years: {min(available_years)} to {max(available_years)}")
    
except Exception as e:
    logger.error(f"Error loading initial data: {e}", exc_info=True)
    exit(1)

# Initialize the Dash app with RTL support
app = dash.Dash(__name__, 
                meta_tags=[
                    {"name": "viewport", "content": "width=device-width, initial-scale=1"}
                ])
server = app.server  # Expose Flask server for Heroku

# Fix dropdown behavior and improve mobile hover display

# Update the index_string with improved mobile styles and JavaScript
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
            
            /* Prevent keyboard from opening on mobile */
            .Select-input > input {
                opacity: 0;
                position: absolute;
                /* Remove cursor pointer which causes issues */
                cursor: default;
                /* Disable all keyboard input interactions */
                pointer-events: none !important;
                touch-action: none !important;
            }
            
            /* Fix dropdown appearance and focus issues */
            .Select-control {
                cursor: pointer !important;
            }
            .Select-value {
                pointer-events: none;
            }
            
            /* Improve hover tooltip display on small screens */
            .hoverlayer .hovertext {
                max-width: 300px !important;
                white-space: normal !important;
                font-size: 13px !important;
            }
            
            /* Mobile-specific styles */
            @media (max-width: 768px) {
                .control-item {
                    width: 100% !important;
                    margin-left: 0 !important;
                    margin-bottom: 10px;
                }
                
                .results-item {
                    width: 100% !important;
                    margin-left: 0 !important;
                    margin-bottom: 5px;
                }
                
                .control-panel {
                    padding: 8px;
                }
                
                /* Make the graph adjust to screen size */
                .responsive-graph {
                    height: 350px !important;
                }
                
                /* Make hover tooltips better on mobile */
                .hoverlayer .hovertext {
                    max-width: 250px !important;
                    font-size: 12px !important;
                    padding: 5px !important;
                }
            }
        </style>
        
        <!-- Improved JavaScript to handle dropdowns better -->
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                // Function to disable virtual keyboard but keep dropdown open
                function preventKeyboard() {
                    // Find all dropdown inputs
                    const dropdownInputs = document.querySelectorAll('.Select-input > input');
                    dropdownInputs.forEach(input => {
                        // Set attributes to prevent keyboard
                        input.setAttribute('inputmode', 'none');
                        input.setAttribute('readonly', 'readonly');
                        
                        // Don't blur on focus, which causes dropdowns to close immediately
                        input.addEventListener('focus', function(e) {
                            e.preventDefault();
                            // Don't blur - this was causing dropdowns to close right away
                        });
                        
                        // Handle touch events better
                        input.parentElement.parentElement.addEventListener('touchstart', function(e) {
                            // Let the click propagate but prevent keyboard
                            e.stopPropagation();
                        }, true);
                    });
                }
                
                // Apply initially and periodically to catch dynamically created elements
                preventKeyboard();
                setInterval(preventKeyboard, 1000);
            });
        </script>
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

# Update the app layout to use the new responsive classes 
app.layout = html.Div([
    
    # Control panel
    html.Div([
        html.Div([
            # First row with dropdowns - make responsive
            html.Div([
                html.Div([
                    html.Label("אזור"),
                    dcc.Dropdown(
                        id='region-dropdown',
                        options=[{'label': region, 'value': region} for region in available_regions],
                        value='כולם',
                        clearable=False
                    ),
                ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '1%'}, className='control-item'),
                
                html.Div([
                    html.Label("חדרים"),
                    dcc.Dropdown(
                        id='rooms-dropdown',
                        options=[{'label': room, 'value': room} for room in available_room_types],
                        value='הכל',
                        clearable=False
                    ),
                ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '1%'}, className='control-item'),
                
                html.Div([
                    html.Label("שנת התחלה"),
                    dcc.Dropdown(
                        id='start-year-dropdown',
                        options=[{'label': str(year), 'value': year} for year in available_years],
                        value=1994,
                        clearable=False
                    ),
                ], style={'width': '32%', 'display': 'inline-block'}, className='control-item'),
            ], style={'marginBottom': '10px'}),
            
            # Second row with sliders - make responsive
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
                ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '2%'}, className='control-item'),
                
                html.Div([
                    html.Label("אחוז השקעה במניות S&P 500"),
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
                ], style={'width': '48%', 'display': 'inline-block'}, className='control-item'),
            ]),
        ], className='control-panel'),
                
        # Results info panel - make responsive
        html.Div(id='results-info', className='results-panel'),
        
        # Graph area with responsive dimensions
        html.Div([
            dcc.Graph(
                id='investment-comparison-graph',
                config={
                    'displayModeBar': False,
                    'responsive': True  # Make graph responsive
                },
                style={'height': '500px', 'width': '100%'}
            )
        ], style={'marginTop': '10px'}, className='responsive-graph'),
        
        # Footer
        html.Div(
            "מקורות נתונים: הלשכה המרכזית לסטטיסטיקה, תשואות S&P 500, תשואות אג\"ח",
            style={'marginTop': '10px', 'fontSize': 'smaller', 'fontStyle': 'italic', 'textAlign': 'center'}
        )
    ], style={'margin': '0 auto', 'maxWidth': '1200px', 'padding': '10px', 'width': '95%'})  # Adjust container width
])

# Bond allocation callback (unchanged)
@app.callback(
    Output('bond-allocation', 'children'),
    [Input('sp500-slider', 'value')]
)
def update_bond_allocation(sp500_value):
    return f"{100 - sp500_value}%"

# ---- EFFICIENCY FIX 4: HELPER FUNCTIONS FOR REPEATED OPERATIONS ----
def prepare_data_for_plotting(df_apartment, df_market, scale):
    """
    Prepares data for plotting with efficient indexing and customdata creation
    """
    # Set index once for O(1) lookups
    df_apartment_indexed = df_apartment.set_index('Year')
    df_market_indexed = df_market.set_index('Year')
    
    # Prepare apartment customdata efficiently
    apartment_customdata = []
    for year in df_apartment_indexed.index:
        apt_row = df_apartment_indexed.loc[year]
        apartment_customdata.append({
            'תשואה_ריאלית': format_hebrew_number(apt_row['Investment_Return']),
            'שווי_הדירה': format_hebrew_number(apt_row['Price']),
            'יתרת_משכנתא': format_hebrew_number(apt_row['Balance']),
            'כסף_שהושקע': format_hebrew_number(apt_row['Cumulative_Payments']),
            'סהכ_הכנסות_שכירות': format_hebrew_number(apt_row['Cumulative_Rent']),
            'שכד_חודשי': format_hebrew_number(apt_row['Yearly_Rent'] / 12),
            'תשואה_נומינלית': format_hebrew_number(apt_row['Investment_Return_Nominal'])
        })
    
    # Prepare market customdata efficiently
    market_customdata = []
    for year in df_market_indexed.index:
        market_row = df_market_indexed.loc[year]
        market_customdata.append({
            'תשואה_נטו_ריאלית': format_hebrew_number(market_row['Investment_Return']),
            'תשואה_נטו_נומילית': format_hebrew_number(market_row['Net_Profit_Nominal']),
            'שווי_תיק_השקעות': format_hebrew_number(market_row['Portfolio_Value']),
            'השקעה_מצטברת': format_hebrew_number(market_row['Cumulative_Investment']),
            'מס': format_hebrew_number(market_row.get('Tax', 0)),
            'סהכ_עמלות': format_hebrew_number(market_row.get('Total_Fees', 0)),
            'אחוז_השקעה_במניות': f"{market_row.get('SP500_Allocation', '')}%"
        })
    
    # Calculate scaling factors once
    max_value = max(df_apartment['Investment_Return'].max(), df_market['Investment_Return'].max())
    min_value = min(df_apartment['Investment_Return'].min(), df_market['Investment_Return'].min())
    
    return {
        'apartment_customdata': apartment_customdata,
        'market_customdata': market_customdata,
        'max_value': max_value,
        'min_value': min_value,
        'years': sorted(df_apartment['Year'].unique())
    }

def create_standard_graph_layout(suffix, width=None, height=None):
    """
    Creates a standardized graph layout to avoid code duplication
    Now with better mobile support - auto-width and height
    """
    return {
        'autosize': True,  # Allow graph to size automatically
        'margin': dict(l=50, r=50, t=50, b=70),
        'xaxis': dict(
            title=dict(
                text='שנה',
                standoff=15
            ),
            fixedrange=True,
            type='category'
        ),
        'yaxis': dict(
            title=dict(
                text=f'תשואה על השקעה ({suffix} ₪)',
                standoff=30
            ),
            fixedrange=True,
            tickformat=",.1f",
            automargin=True
        ),
        'hovermode': 'closest',
        'dragmode': False,
        'font': dict(family="Arial Hebrew, Arial, sans-serif"),
        'legend': dict(
            title='סוג השקעה',
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    }

def calculate_scale(max_value):
    """Determine appropriate scale for y-axis display"""
    if max_value >= 1_000_000:
        return 1_000_000, 'מיליון'
    elif max_value >= 1_000:
        return 1_000, 'אלף'
    else:
        return 1, ''

# ---- EFFICIENCY FIX 5: OPTIMIZED MAIN CALLBACK ----
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
        # Load apartment and rent data - this is necessary as it's filtered by user selection
        df_preprocessed = load_apartment_data(apartment_region, apartment_rooms)
        rent_df = load_rent_data(apartment_region, apartment_rooms)
        
        # Efficient year checking
        apartment_years = set(df_preprocessed['Year'].unique() if 'Year' in df_preprocessed.columns else [])
        rent_years = set(rent_df['שנה'].unique() if 'שנה' in rent_df.columns else [])
        available_years_for_selection = sorted(apartment_years.intersection(rent_years))
        
        # No data case
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
            
            error_fig, error_message = create_rtl_message(error_title, "red", additional_text)
            return error_fig, error_message
        
        # Year range check
        earliest_year = min(available_years_for_selection)
        latest_year = max(available_years_for_selection)
        
        if start_year > latest_year or start_year < earliest_year:
            error_title = f'אזור זה זמין רק בין השנים {earliest_year} ו-{latest_year}'
            error_fig, error_message = create_rtl_message(error_title, "orange")
            return error_fig, error_message
        
        # Filter data efficiently
        df_preprocessed = df_preprocessed[df_preprocessed['Year'] >= start_year]
        if len(df_preprocessed) == 0:
            empty_title = 'אין נתונים זמינים לשנים שנבחרו'
            empty_fig, empty_message = create_rtl_message(empty_title, "red")
            return empty_fig, empty_message
        
        # ---- EFFICIENCY FIX 6: USE PRELOADED DATA ----
        # No need to reload these - use the global variables
        # Calculate inflation factors just once
        inflation_factors = calculate_inflation_factors(df_cpi, start_year)
        
        # Get interest rate - this is a fast operation so no need to optimize
        interest_rate = get_interest_rate(interest_rates, loan_term_years)
        
        # Get initial property price
        initial_price = df_preprocessed.loc[df_preprocessed['Year'].idxmin(), 'Price']
        
        # These functions do the heavy lifting calculations
        df_apartment = calculate_investment_metrics(
            df_preprocessed, start_year, initial_price, 
            interest_rate, loan_term_years, rent_df, 
            apartment_region, apartment_rooms, inflation_factors
        )
        
        # Add SP500 allocation to the data for hover info
        df_market = calculate_portfolio_performance(
            df_preprocessed, start_year, initial_price, 
            interest_rate, loan_term_years, stock_returns, 
            bond_returns, sp500_allocation, inflation_factors
        )
        df_market['SP500_Allocation'] = sp500_allocation
        
        # ---- EFFICIENCY FIX 7: EFFICIENT PLOTTING CODE ----
        # Calculate scale for display once
        scale, suffix = calculate_scale(max(
            df_apartment['Investment_Return'].max(), 
            df_market['Investment_Return'].max()
        ))
        
        # Prepare data for plotting - efficient customdata generation
        plot_data = prepare_data_for_plotting(df_apartment, df_market, scale)
        
        # Create figure with standardized layout
        fig = go.Figure()
        
        # Add traces efficiently
        fig.add_trace(go.Scatter(
            x=df_apartment['Year'],
            y=df_apartment['Investment_Return'] / scale,
            name='דירה',
            line=dict(color='#1f77b4'),
            customdata=plot_data['apartment_customdata'],
            hovertemplate=
                "<b>דירה</b><br><br>" +
                "<b>פרטים כלליים:</b><br>" +
                "שנה: %{x}<br>" +
                "תשואה ריאלית: %{customdata.תשואה_ריאלית}<br><br>" +
                "<b>פרטים נוספים:</b><br>" +
                "שווי הדירה: %{customdata.שווי_הדירה}<br>" +
                "יתרת משכנתא: %{customdata.יתרת_משכנתא}<br>" +
                "כסף שהושקע: %{customdata.כסף_שהושקע}<br>" +
                "שכ\" ד חודשי (אחרי תחזוקה): %{customdata.שכד_חודשי}<br>" +
                "סה\"כ הכנסות שכירות: %{customdata.סהכ_הכנסות_שכירות}<br>" +
                "תשואה נומינלית: %{customdata.תשואה_נומינלית}<br>" +
                "<extra></extra>"
        ))
        
        fig.add_trace(go.Scatter(
            x=df_market['Year'],
            y=df_market['Investment_Return'] / scale,
            name='תיק השקעות',
            line=dict(color='#ff7f0e'),
            customdata=plot_data['market_customdata'],
            hovertemplate=
                "<b>תיק השקעות</b><br><br>" +
                "<b>פרטים כלליים:</b><br>" +
                "שנה: %{x}<br>" +
                "תשואה נטו ריאלית: %{customdata.תשואה_נטו_ריאלית}<br><br>" +
                "<b>פרטים נוספים:</b><br>" +
                "תשואה נטו נומינלית: %{customdata.תשואה_נטו_נומילית}<br>" +
                "שווי תיק השקעות: %{customdata.שווי_תיק_השקעות}<br>" +
                "סה\"כ השקעה: %{customdata.השקעה_מצטברת}<br>" +
                "מס: %{customdata.מס}<br>" +
                "עמלות: %{customdata.סהכ_עמלות}<br>" +
                "אחוז השקעה במניות: %{customdata.אחוז_השקעה_במניות}<br>" +
                "<extra></extra>"
        ))
        
        # Add standardized layout
        fig.update_layout(create_standard_graph_layout(suffix))
        
        # ---- EFFICIENCY FIX 8: CALCULATE RESULTS ONCE ----
        # Get first and last year data efficiently
        df_apartment_indexed = df_apartment.set_index('Year')
        df_market_indexed = df_market.set_index('Year')
        
        latest_year = max(df_apartment['Year'])
        apt_final_return = df_apartment_indexed.loc[latest_year, 'Investment_Return']
        market_final_return = df_market_indexed.loc[latest_year, 'Investment_Return']
        
        # Calculate area under curve just once
        apt_area = df_apartment['Investment_Return'].sum()
        market_area = df_market['Investment_Return'].sum()
        winner = "דירה" if apt_area > market_area else "תיק השקעות"
        
        # Calculate real price just once
        first_apt_row = df_apartment_indexed.loc[start_year]
        real_apt_price = first_apt_row['Price'] * first_apt_row['Inflation_Factor']
        
        # ---- EFFICIENCY FIX 9: STREAMLINED RESULTS DIV ----
        # Create results info div
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
                    html.Strong("מחיר דירה ריאלי: "), format_hebrew_number(real_apt_price)
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
        logger.error(f"Error updating graph: {e}", exc_info=True)
        error_title = 'שגיאה בהצגת הנתונים'
        error_fig, error_message = create_rtl_message(error_title, "red")
        return error_fig, error_message

# Run the app
if __name__ == '__main__':
    # Get port from environment variable (Heroku sets this)
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=False, host='0.0.0.0', port=port)