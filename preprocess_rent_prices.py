import pandas as pd
import re

# Load the Excel file
try:
    file_path = 'Data/Before preprocessing/rent_prices.xlsx'
    df = pd.read_excel(file_path, engine='openpyxl')
    print(f"Successfully loaded file: {file_path}")
    print("Columns in the file:", df.columns.tolist())
except FileNotFoundError:
    print(f"Error: File '{file_path}' not found. Please check the file path.")
    exit(1)
except Exception as e:
    print(f"Error loading file: {e}")
    exit(1)

# Step 1: Identify the area and room column
area_room_col = None
for col in df.columns:
    if 'אזור' in str(col) and 'חדרים' in str(col):
        area_room_col = col
        break

if area_room_col:
    # Function to separate area and room number
    def separate_area_room(value):
        if pd.isna(value):
            return None, None
        
        value = str(value).strip()
        
        # Pattern 1: Simple area names
        if '(' not in value and '-' not in value:
            return value, 'הכל'
        
        # Pattern 2: Room number ranges with area names
        match = re.match(r'([\d.-]+)\s*\(([^)]+)\)', value)
        if match:
            room_range, area = match.groups()
            area = re.sub(r'\s*-\s*\d+', '', area).strip()
            return area, room_range
        
        # Pattern 3: Area names with codes
        match = re.match(r'([^()]+?)\s*-\s*\d+', value)
        if match:
            area = match.group(1).strip()
            return area, 'הכל'
        
        return value, 'הכל'

    try:
        df[['אזור', 'חדרים בדירה']] = df[area_room_col].apply(lambda x: pd.Series(separate_area_room(x)))
        print(f"Successfully separated '{area_room_col}' into 'אזור' and 'חדרים בדירה'")
        
        # Replace "סך הכל" with "כולם" in the 'אזור' column
        df['אזור'] = df['אזור'].replace('סך הכל', 'כולם')
        print('Replaced "סך הכל" with "כולם" in the "אזור" column')
    except Exception as e:
        print(f"Error during column separation: {e}")
else:
    print("Warning: Area and room column not found. Skipping separation.")

# Step 2: Update annual average with quarterly averages
# Identify quarterly columns (assuming they follow a pattern with months)
quarterly_cols = []
annual_avg_col = None

for col in df.columns:
    col_str = str(col)
    if any(month in col_str for month in ['ינואר', 'אפריל', 'יולי', 'אוקטובר']):
        quarterly_cols.append(col)
    if 'ממוצע' in col_str or 'שנתי' in col_str:
        annual_avg_col = col

if quarterly_cols and annual_avg_col:
    try:
        # Ensure quarterly columns are numeric
        for col in quarterly_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculate the mean of the quarterly columns for each row
        df[annual_avg_col] = df[quarterly_cols].mean(axis=1)
        print(f"Updated '{annual_avg_col}' with the average of quarterly columns")
    except Exception as e:
        print(f"Error calculating annual average: {e}")
else:
    print("Warning: Quarterly columns or annual average column not found. Skipping average calculation.")

# Save the updated DataFrame to a new Excel file
try:
    output_path = 'preprocessed_rent_prices.xlsx'
    df.to_excel(output_path, index=False, engine='openpyxl')
    print(f"Processed data saved to '{output_path}'")
except Exception as e:
    print(f"Error saving file: {e}")