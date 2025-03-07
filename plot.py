import pandas as pd
import plotly.express as px
from dateutil.relativedelta import relativedelta

# Load the CSV files with date parsing
df_hpi = pd.read_csv('Data/HPI.csv', parse_dates=['Month'], dayfirst=True)
df_interest = pd.read_csv('Data/mortgage_interest.csv', parse_dates=['Starting'], dayfirst=True)

# Define input parameters
x = 25  # Loan term in years
y = 2   # Month for interest rate (February)
z = 2025  # Year for interest rate

# Set the mortgage start date as the first month in HPI.csv
start_date = df_hpi['Month'].iloc[0]  # e.g., 2024-02-01 if treated as 2024

# Define the target date for interest rate retrieval
target_date = pd.to_datetime(f'01/{y:02d}/{z}', dayfirst=True)

# Find the row in mortgage_interest.csv with the closest date to target_date
interest_row = df_interest.iloc[(df_interest['Starting'] - target_date).abs().argsort()[0]]

# Map loan term to the appropriate column in mortgage_interest.csv
term_columns = {
    (25, float('inf')): 'More than 25',
    (20, 25): 'From 20 to 25',
    (15, 20): 'From 15 to 20',
    (10, 15): 'From 10 to 15',
    (5, 10): 'From 5 to 10',
    (1, 5): 'From 1 to 5',
    (0, 1): 'Up to and'
}
for (min_years, max_years), column in term_columns.items():
    if min_years < x <= max_years:
        term_column = column
        break

# Get the annual interest rate and convert to monthly
interest_rate_annual = interest_row[term_column] / 100  # e.g., 5.01% for "From 20 to 25" on 13/02/2025
r_monthly = interest_rate_annual / 12

# Mortgage parameters
P = df_hpi['Price'].iloc[0]  # Initial purchase price, e.g., 443.7
n = x * 12  # Total number of payments

# Calculate monthly mortgage payment
if r_monthly == 0:
    M = P / n  # Handle zero interest rate case
else:
    M = P * (r_monthly * (1 + r_monthly)**n) / ((1 + r_monthly)**n - 1)

# Calculate number of months since start_date for each row
df_hpi['k'] = df_hpi['Month'].apply(
    lambda d: relativedelta(d, start_date).years * 12 + relativedelta(d, start_date).months
)

# Function to calculate remaining mortgage balance after k payments
def remaining_balance(k, P, r, M, n):
    if k <= 0:
        return P  # Before or at start, balance is full loan amount
    elif k > n:
        return 0  # After loan term, balance is zero
    else:
        # Remaining balance formula
        if r != 0:
            return P * (1 + r)**k - M * ((1 + r)**k - 1) / r
        else:
            return P - M * k  # Zero interest case
# Calculate remaining balance for each month
df_hpi['Balance'] = df_hpi['k'].apply(lambda k: remaining_balance(k, P, r_monthly, M, n))

# Calculate current value of the investment (equity)
df_hpi['Investment_Value'] = df_hpi['Price'] - df_hpi['Balance']

# Calculate cumulative payments made up to each month
df_hpi['Cumulative_Payments'] = df_hpi['k'] * M

# Calculate investment return (equity minus total payments made)
df_hpi['Investment_Return'] = df_hpi['Investment_Value'] - df_hpi['Cumulative_Payments']

# Create an interactive line plot with 'Month' vs 'Investment_Value'
fig = px.line(
    df_hpi,
    x='Month',
    y='Investment_Return',
    title='Current Value of Investment in Israel Apartment'
)

# Customize the layout
fig.update_layout(
    xaxis_title='Month',
    yaxis_title='Investment Value (Price - Remaining Mortgage Balance)'
)

# Display the plot
fig.show()