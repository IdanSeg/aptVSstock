import pandas as pd
import numpy as np

# Load the preprocessed data
try:
    file_path = 'preprocessed_apt_prices.xlsx'
    df = pd.read_excel(file_path, engine='openpyxl')
    print(f"Successfully loaded file: {file_path}")
except FileNotFoundError:
    print(f"Error: File '{file_path}' not found. Please check the file path.")
    exit(1)
except Exception as e:
    print(f"Error loading file: {e}")
    exit(1)

# Preprocess data
df['אזור'] = df['אזור'].astype(str)
df.loc[df['אזור'] == 'nan', 'אזור'] = np.nan
df = df.dropna(subset=['אזור'])
df_filtered = df[df['חדרים בדירה'] == 'הכל']

# Define region pairs and cities
region_pairs = [
    ("המרכז וסובב ירושלים", "מחוז ירושלים"),
    ("הדרום", "מחוז דרום"),
    ("גוש דן", "מחוז תל אביב"),
    ("הצפון", "מחוז צפון"),
    ("קריות חיפה", "מחוז חיפה")
]
individual_cities = ["תל אביב", "חיפה", "ירושלים"]

# Modified function to check for cross-year availability in pairs
def calculate_cross_year_change(region1_data, region2_data):
    # Check all possible combinations of years between the two regions
    for year1 in [2016, 2017]:
        for year2 in [2016, 2017]:
            price1 = region1_data.get(year1)
            price2 = region2_data.get(year2)
            if price1 is not None and price2 is not None:
                return {
                    'start_year': year1,
                    'end_year': year2,
                    'price1': price1,
                    'price2': price2,
                    'change_pct': ((price2 - price1)/price1)*100
                }
    return None

# Process region pairs with cross-year checks
print("\nPrice changes between region pairs (2016-2017):")
for region1, region2 in region_pairs:
    # Get all available price data for both regions
    r1_prices = df_filtered[df_filtered['אזור'] == region1].set_index('שנה')['ממוצע שנתי'].to_dict()
    r2_prices = df_filtered[df_filtered['אזור'] == region2].set_index('שנה')['ממוצע שנתי'].to_dict()
    
    # Check for any valid year combination
    result = calculate_cross_year_change(r1_prices, r2_prices)
    
    if result:
        print(f"\n{region1} ({result['start_year']}) vs {region2} ({result['end_year']}):")
        print(f"{region1}: {result['price1']:.2f} ({result['start_year']})")
        print(f"{region2}: {result['price2']:.2f} ({result['end_year']})")
        print(f"Change: {result['change_pct']:.2f}%")
        print("-" * 60)
    else:
        print(f"\nNo valid year combination found for {region1} vs {region2}")
        print("-" * 60)

# Process individual cities (original logic remains)
print("\nPrice changes for individual cities (2016-2017):")
def calculate_price_change(city):
    city_data = df_filtered[df_filtered['אזור'] == city]
    if {2016, 2017}.issubset(city_data['שנה']):
        p2016 = city_data.loc[city_data['שנה'] == 2016, 'ממוצע שנתי'].values[0]
        p2017 = city_data.loc[city_data['שנה'] == 2017, 'ממוצע שנתי'].values[0]
        return {
            'city': city,
            'change': ((p2017 - p2016)/p2016)*100
        }
    return None

for city in individual_cities:
    result = calculate_price_change(city)
    if result:
        print(f"\n{city}: {result['change']:.2f}% change (2016-2017)")
    else:
        print(f"\n{city}: Insufficient data for 2016-2017")
    print("-" * 60)