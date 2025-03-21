import pandas as pd
import plotly.express as px
import numpy as np

def load_apartment_data(region, rooms):
    """Load and preprocess apartment price data."""
    try:
        df = pd.read_excel('preprocessed_apt_prices.xlsx', engine='openpyxl')
        print("Successfully loaded preprocessed dataset.")
        
        # Use year as our time period and price average as our property value
        df['Year'] = df['שנה']
        df['Price'] = df['ממוצע שנתי']
        
        # Filter for specific region and room count
        df = df[(df['אזור'] == region) & (df['חדרים בדירה'] == rooms)]
        
        # Convert Year to numeric if it's not already
        df['Year'] = pd.to_numeric(df['Year'])
        
        print(f"Created Year and Price columns. {len(df)} rows after filtering.")
        return df
    except FileNotFoundError:
        print("Error: File 'preprocessed_apt_prices.xlsx' not found. Please check the file path.")
        exit(1)
    except Exception as e:
        print(f"Error loading file: {e}")
        exit(1)

def load_rent_data(region, rooms):
    """Load and preprocess rent price data."""
    try:
        df_rent = pd.read_excel('preprocessed_rent_prices.xlsx', engine='openpyxl')
        print("Successfully loaded rent prices dataset.")
        
        # Filter for specific region and room count
        relevant_rent_data = df_rent[(df_rent['אזור'] == region) & 
                                        (df_rent['חדרים בדירה'] == rooms)]
        
        # Extract yearly rent values
        rent_df = relevant_rent_data[['שנה', 'ממוצע שנתי']].sort_values(by='שנה')
        rent_df['שנה'] = pd.to_numeric(rent_df['שנה'])  # Ensure year is numeric
        
        return rent_df
    except FileNotFoundError:
        print("Error: File 'preprocessed_rent_prices.xlsx' not found. Please check the file path.")
        exit(1)
    except Exception as e:
        print(f"Error loading rent prices file: {e}")
        exit(1)

def load_interest_rates():
    """Load mortgage interest rate data."""
    try:
        df_interest = pd.read_csv('Data/mortgage_interest.csv', parse_dates=['Starting'], dayfirst=True)
        print("Successfully loaded mortgage interest rates dataset.")
        
        # Use the first row of interest rate data
        interest_row = df_interest.iloc[0]
        print(f"Using interest rate data from: {interest_row['Starting']}")
        
        return interest_row
    except FileNotFoundError:
        print("Error: File 'mortgage_interest.csv' not found. Please check the file path.")
        exit(1)
    except Exception as e:
        print(f"Error loading file: {e}")
        exit(1)

def load_cpi_data():
    """Load and process inflation (CPI) data."""
    try:
        df_cpi = pd.read_csv('CPI.csv')
        print("Successfully loaded CPI dataset.")
        
        # Convert 'Total' and 'Year' to numeric
        if df_cpi['Total'].dtype == object:
            df_cpi['Total'] = df_cpi['Total'].str.strip().astype(float)
        else:
            df_cpi['Total'] = df_cpi['Total'].astype(float)
        
        if df_cpi['Year'].dtype == object:
            df_cpi['Year'] = df_cpi['Year'].str.strip().astype(int)
        else:
            df_cpi['Year'] = df_cpi['Year'].astype(int)
        
        # Keep only Year and Total columns
        df_cpi = df_cpi[['Year', 'Total']]
        return df_cpi
    except FileNotFoundError:
        print("Error: File 'CPI.csv' not found. Please check the file path.")
        exit(1)
    except Exception as e:
        print(f"Error loading CPI file: {e}")
        exit(1)

def get_interest_rate(interest_row, loan_term):
    """Get the appropriate interest rate based on loan term."""
    term_columns = {
        (25, float('inf')): 'More than 25',
        (20, 25): 'From 20 to 25',
        (15, 20): 'From 15 to 20',
        (10, 15): 'From 10 to 15',
        (5, 10): 'From 5 to 10',
        (1, 5): 'From 1 to 5',
    }
    
    for (min_years, max_years), column in term_columns.items():
        if min_years < loan_term <= max_years:
            return interest_row[column] / 100
    
    return interest_row['Average'] / 100

def calculate_mortgage_payment(loan_amount, interest_rate, term_years):
    """Calculate the monthly mortgage payment."""
    r_monthly = interest_rate / 12
    n_months = term_years * 12
    if r_monthly == 0:
        return loan_amount / n_months
    else:
        # the amortization formula
        return loan_amount * (r_monthly * (1 + r_monthly)**n_months) / ((1 + r_monthly)**n_months - 1)

def remaining_balance(k, P, r_annual, A, n):
    """Calculate remaining mortgage balance after k years."""
    if k <= 0:
        return P
    elif k > n:
        return 0
    else:
        r_monthly = r_annual / 12
        months = k * 12
        M = A / 12
        if r_monthly != 0:
            return P * (1 + r_monthly)**months - M * ((1 + r_monthly)**months - 1) / r_monthly
        else:
            return P - M * months

def get_monthly_rent(year, rent_df, region, rooms):
    """Get monthly rent for a specific year."""
    if len(rent_df) == 0:
        print(f"Warning: No rent data available for {region} with {rooms} rooms")
        return 0
        
    matching_row = rent_df[rent_df['שנה'] == year]
    if not matching_row.empty:
        return matching_row['ממוצע שנתי'].values[0]
    else:
        raise ValueError(f"No rent data found for year {year}")

def calculate_cumulative_rent(row, df, start_year, rent_df, region, rooms):
    """Calculate cumulative rental income for a given row."""
    if row['k'] <= 0:
        return 0
    
    years_needed = list(range(start_year, start_year + int(row['k'])))
    years_available = sorted(df['Year'].unique())
    missing_years = [yr for yr in years_needed if yr not in years_available]
    if missing_years:
        raise ValueError(f"Missing rent data for years: {missing_years}")
    
    total_rent = sum(
        df[(df['Year'] >= start_year) & 
            (df['Year'] < start_year + row['k'])]['Yearly_Rent'].tolist()
    )
    return total_rent

def calculate_inflation_factors(df_cpi, start_year, base_cpi=100):
    """Calculate inflation factors from annual CPI % changes relative to latest year."""
    df_cpi = df_cpi.sort_values('Year')
    
    # Use whichever column name exists for % change
    cpi_column = 'Total'  # Default
    if 'CPI' in df_cpi.columns:
        cpi_column = 'CPI'
    elif 'מדד' in df_cpi.columns:
        cpi_column = 'מדד'
    
    # Convert % changes to absolute CPI values
    cpi_values = {}
    previous_cpi = base_cpi
    for _, row in df_cpi.iterrows():
        year = row['Year']
        cpi_change = row[cpi_column] / 100  # Convert % to decimal (e.g., 2.8 -> 0.028)
        current_cpi = previous_cpi * (1 + cpi_change)
        cpi_values[year] = current_cpi
        previous_cpi = current_cpi
    
    # Latest CPI (2024 in your case)
    latest_cpi = cpi_values[df_cpi['Year'].iloc[-1]]
    
    # Calculate inflation factors to adjust to latest year
    inflation_factors = {}
    for year, cpi in cpi_values.items():
        inflation_factors[year] = latest_cpi / cpi  # Corrected to adjust TO latest year
    
    return inflation_factors

def calculate_investment_metrics(df, start_year, P, interest_rate, term_years, rent_df, region, rooms, inflation_factors):
    """Calculate all investment metrics for the apartment, adjusted for inflation."""
    down_payment = P * 0.25
    mortgage_amount = P * 0.75
    M = calculate_mortgage_payment(mortgage_amount, interest_rate, term_years)
    A = M * 12
    
    df['k'] = df['Year'] - start_year
    df['Balance'] = df['k'].apply(
        lambda k: remaining_balance(k, mortgage_amount, interest_rate, A, term_years)
    )
    df['Investment_Value'] = df['Price'] - df['Balance']
    
    df['Cumulative_Payments'] = df.apply(
        lambda row: down_payment + (min(row['k'], term_years) * A),
        axis=1
    )
    
    df['Yearly_Rent_Gross'] = df['Year'].apply(
        lambda y: get_monthly_rent(y, rent_df, region, rooms) * 12
    )
    df['Maintenance_Cost'] = df['Yearly_Rent_Gross'] * 0.15
    df['Yearly_Rent'] = df['Yearly_Rent_Gross'] - df['Maintenance_Cost']
    df['Cumulative_Rent'] = df.apply(
        lambda row: calculate_cumulative_rent(row, df, start_year, rent_df, region, rooms),
        axis=1
    )
    df['Investment_Return_Nominal'] = (
        df['Investment_Value'] - 
        df['Cumulative_Payments'] + 
        df['Cumulative_Rent']
    )
    df['Inflation_Factor'] = df['Year'].map(inflation_factors)
    missing_inflation_years = df[df['Inflation_Factor'].isna()]['Year'].tolist()
    if missing_inflation_years:
        raise ValueError(f"Missing inflation data for years: {missing_inflation_years}")
    
    # Revert to original calculation for the inflation-adjusted return
    df['Investment_Return'] = df['Investment_Return_Nominal'] * df['Inflation_Factor']
    
    return df

def create_plot(df_apt, df_market):
    """Create and display the inflation-adjusted investment return plot for both apartment and market."""
    df_apt_plot = df_apt[['Year', 'Investment_Return']].copy()
    df_apt_plot['Investment_Type'] = 'Apartment'
    
    df_market_plot = df_market[['Year', 'Investment_Return']].copy()
    df_market_plot['Investment_Type'] = 'Market Portfolio'
    
    combined_df = pd.concat([df_apt_plot, df_market_plot], ignore_index=True)
    
    fig = px.line(
        combined_df,
        x='Year',
        y='Investment_Return',
        color='Investment_Type',
        title='Real Return on Investment (Inflation Adjusted)',
        labels={'Investment_Return': 'Investment Return (₪ in today\'s money)'}
    )
    fig.update_layout(
        xaxis_title='Year',
        yaxis_title='Investment Return (₪ in today\'s money)',
        legend_title='Investment Type'
    )
    fig.show()

def load_stock_returns():
    """Load S&P 500 historical total returns (price + dividends)."""
    try:
        # Read CSV with headers (since the file now has proper column names)
        df = pd.read_csv('Data/sp.csv', delim_whitespace=True)
        print("Successfully loaded S&P 500 returns dataset.")
        
        # Validate the required column exists
        if 'Total-Return' not in df.columns:
            raise ValueError("S&P 500 data missing 'Total-Return' column")
        
        # Convert Total-Return to numeric values
        df['Total-Return'] = pd.to_numeric(df['Total-Return'], errors='coerce')
        
        # Check for NaN values
        if df['Total-Return'].isna().any():
            nan_years = df[df['Total-Return'].isna()]['Year'].tolist()
            print(f"Warning: Missing S&P 500 return data for years: {nan_years}")
        
        # Set Year as index and return the Total-Return column
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        
        print(f"Using S&P 500 total returns (including dividends) from {df['Year'].min()} to {df['Year'].max()}")
        
        return df.set_index('Year')['Total-Return']
    except FileNotFoundError:
        print("Error: File 'Data/s&p.csv' not found. Please check the file path.")
        exit(1)
    except Exception as e:
        print(f"Error loading S&P 500 returns: {e}")
        exit(1)

def load_bond_returns():
    """Load bond historical returns (BND.csv) with multiple columns, ensuring 'Return' is numeric."""
    try:
        df = pd.read_csv('Data/BND.csv')
        print("Successfully loaded Bond returns dataset.")
        
        # Make sure the 'Return' column exists and is numeric
        if 'Return' not in df.columns:
            raise ValueError("BND.csv missing 'Return' column.")
        df['Return'] = pd.to_numeric(df['Return'], errors='coerce')
        
        # Retain only 'Year' and 'Return'
        df = df[['Year', 'Return']]
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        
        return df.set_index('Year')['Return']
    except FileNotFoundError:
        print("Error: File 'Data/BND.csv' not found. Please check the file path.")
        exit(1)
    except Exception as e:
        print(f"Error loading Bond returns: {e}")
        exit(1)

# Fix portfolio performance to be consistent

def calculate_portfolio_performance(df, start_year, initial_price, interest_rate, term_years, stock_returns, bond_returns, sp500_allocation, inflation_factors):
    """
    Calculate performance of an equivalent stock/bond portfolio 
    with the same cash flows as the apartment investment.
    """
    # First part remains unchanged...
    down_payment = initial_price * 0.25
    mortgage_amount = initial_price * 0.75
    
    M = calculate_mortgage_payment(mortgage_amount, interest_rate, term_years)
    A = M * 12
    
    years = sorted(df['Year'].unique())
    
    # Initial investment minus 0.5% fee - this is the initial exchange fee
    initial_exchange_fee = down_payment * 0.005
    initial_investment = down_payment - initial_exchange_fee
    
    portfolio_df = pd.DataFrame(
        index=years, 
        columns=['Year', 'Portfolio_Value', 'Cumulative_Investment', 'Annual_Cost', 'Investment_Return']
    )
    portfolio_df['Year'] = years
    
    current_value = initial_investment
    cumulative_investment = down_payment
    
    # Track all fees separately
    portfolio_df['Initial_Exchange_Fee'] = 0.0
    portfolio_df.loc[portfolio_df.index[0], 'Initial_Exchange_Fee'] = initial_exchange_fee
    
    portfolio_df['Monthly_Exchange_Fees'] = 0.0
    portfolio_df['Cumulative_Monthly_Exchange_Fees'] = 0.0  # Add this new column
    portfolio_df['Annual_Management_Fees'] = 0.0
    portfolio_df['Cumulative_Management_Fees'] = 0.0
    
    # Portfolio growth calculation
    for i, year in enumerate(years):
        if i == 0:
            portfolio_df.loc[year, 'Portfolio_Value'] = current_value
            portfolio_df.loc[year, 'Cumulative_Investment'] = down_payment
            
            # Annual management fee (0.03%)
            annual_management_fee = current_value * 0.0003
            portfolio_df.loc[year, 'Annual_Cost'] = annual_management_fee
            portfolio_df.loc[year, 'Annual_Management_Fees'] = annual_management_fee
            portfolio_df.loc[year, 'Cumulative_Management_Fees'] = annual_management_fee
            portfolio_df.loc[year, 'Cumulative_Monthly_Exchange_Fees'] = 0.0  # Initialize
        else:
            prev_value = portfolio_df.loc[years[i - 1], 'Portfolio_Value']
            prev_cumulative_fees = portfolio_df.loc[years[i - 1], 'Cumulative_Management_Fees']
            prev_cumulative_exchange_fees = portfolio_df.loc[years[i - 1], 'Cumulative_Monthly_Exchange_Fees']  # Get previous total
            
            stock_return = stock_returns.get(year, 0) / 100
            bond_return = bond_returns.get(year, 0) / 100
            weighted_return = (sp500_allocation/100)*stock_return + ((100-sp500_allocation)/100)*bond_return
            
            monthly_return = (1 + weighted_return)**(1/12) - 1
            current_value = prev_value
            
            years_passed = year - start_year
            monthly_exchange_fees = 0.0
            
            if years_passed <= term_years:
                # 0.5% exchange fee on monthly investments
                monthly_exchange_fee = M * 0.005
                monthly_investment = M - monthly_exchange_fee
                monthly_exchange_fees = monthly_exchange_fee * 12
                
                for month in range(12):
                    current_value *= (1 + monthly_return)
                    current_value += monthly_investment
                
                actual_annual_investment = M * 12
                cumulative_investment += actual_annual_investment
            else:
                current_value *= (1 + weighted_return)
            
            # Annual management fee (0.03%)
            annual_management_fee = current_value * 0.0003
            current_value -= annual_management_fee
            
            portfolio_df.loc[year, 'Portfolio_Value'] = current_value
            portfolio_df.loc[year, 'Cumulative_Investment'] = cumulative_investment
            portfolio_df.loc[year, 'Annual_Cost'] = annual_management_fee
            portfolio_df.loc[year, 'Annual_Management_Fees'] = annual_management_fee
            portfolio_df.loc[year, 'Monthly_Exchange_Fees'] = monthly_exchange_fees
            portfolio_df.loc[year, 'Cumulative_Monthly_Exchange_Fees'] = prev_cumulative_exchange_fees + monthly_exchange_fees
            portfolio_df.loc[year, 'Cumulative_Management_Fees'] = prev_cumulative_fees + annual_management_fee
    
    # Fixed calculation flow that properly accounts for all fees and taxes:
    
    # 1. Calculate final exchange fee (0.2% when selling)
    portfolio_df['Final_Exchange_Fee'] = portfolio_df['Portfolio_Value'] * 0.002
    
    # 2. Portfolio value after all fees (including final exchange fee)
    portfolio_df['Portfolio_Value_After_Fees'] = portfolio_df['Portfolio_Value'] - portfolio_df['Final_Exchange_Fee']
    
    # 3. Calculate total fees - use Cumulative_Monthly_Exchange_Fees instead of Monthly_Exchange_Fees
    portfolio_df['Total_Fees'] = (
        portfolio_df['Initial_Exchange_Fee'] + 
        portfolio_df['Cumulative_Monthly_Exchange_Fees'] +  # Use cumulative value 
        portfolio_df['Cumulative_Management_Fees'] + 
        portfolio_df['Final_Exchange_Fee']
    )
    
    # 4. Calculate pre-tax profit (after all fees have been deducted)
    portfolio_df['Profit_Pretax'] = (
        portfolio_df['Portfolio_Value_After_Fees'] - portfolio_df['Cumulative_Investment']
    )
    
    # 5. Calculate tax (only on positive profits after fees)
    portfolio_df['Tax'] = np.where(
        portfolio_df['Profit_Pretax'] > 0, 
        portfolio_df['Profit_Pretax'] * 0.25, 
        0
    )
    
    # 6. Calculate net profit after taxes
    portfolio_df['Net_Profit_Nominal'] = portfolio_df['Profit_Pretax'] - portfolio_df['Tax']
    
    # 7. Apply inflation adjustment to get real values
    portfolio_df['Inflation_Factor'] = portfolio_df['Year'].map(inflation_factors)
    
    missing_inflation_years = portfolio_df[portfolio_df['Inflation_Factor'].isna()]['Year'].tolist()
    if missing_inflation_years:
        raise ValueError(f"Missing inflation data for market portfolio in years: {missing_inflation_years}")
    
    # CONSISTENT approach: use net profit divided by inflation factor
    portfolio_df['Investment_Return'] = portfolio_df['Net_Profit_Nominal'] * portfolio_df['Inflation_Factor']
    
    return portfolio_df

def main():
    """Main execution function."""
    # Input parameters
    apartment_region = 'הצפון'
    apartment_rooms = 'הכל'
    loan_term_years = 30
    start_year = 1995
    sp500_allocation = 80
    
    df_preprocessed = load_apartment_data(apartment_region, apartment_rooms)
    rent_df = load_rent_data(apartment_region, apartment_rooms)
    interest_row = load_interest_rates()
    df_cpi = load_cpi_data()
    stock_returns = load_stock_returns()
    bond_returns = load_bond_returns()
    
    # Filter data to only include years from start_year onwards
    df_preprocessed = df_preprocessed[df_preprocessed['Year'] >= start_year]
    if len(df_preprocessed) == 0:
        raise ValueError(f"No apartment data available for {apartment_region} with {apartment_rooms} rooms from year {start_year}")
    
    inflation_factors = calculate_inflation_factors(df_cpi, start_year)
    interest_rate = get_interest_rate(interest_row, loan_term_years)
    
    initial_price = df_preprocessed.loc[df_preprocessed['Year'].idxmin(), 'Price']
    print(f"Initial property price: ₪{initial_price:.2f}")
    print(f"Down payment (25%): ₪{initial_price * 0.25:.2f}")
    print(f"Mortgage amount (75%): ₪{initial_price * 0.75:.2f}")
    print(f"Loan term: {loan_term_years} years")
    print(f"Interest rate: {interest_rate*100:.2f}%")
    print(f"Starting analysis from year: {start_year}")
    print(f"S&P 500 allocation: {sp500_allocation}%")
    print(f"Bond allocation: {100 - sp500_allocation}%")
    print(f"Inflation adjustment: Applied (values shown in terms of {df_cpi['Year'].max()} money)")
    
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
    
    # Create and display the comparative plot
    create_plot(df_apartment, df_market)

if __name__ == "__main__":
    main()