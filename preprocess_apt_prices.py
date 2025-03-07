import pandas as pd
import re

# Load the Excel file
try:
    file_path = 'Data/Before preprocessing/apt_prices.xlsx'  # Replace with your actual file path
    df = pd.read_excel(file_path, engine='openpyxl')
    print(f"Successfully loaded file: {file_path}")
except FileNotFoundError:
    print(f"Error: File '{file_path}' not found. Please check the file path.")
    exit(1)
except Exception as e:
    print(f"Error loading file: {e}")
    exit(1)

# Verify required columns exist
required_columns = ['קוד', 'אזור וחדרים בדירה', 'מטבע', 'שנה', 'ממוצע שנתי', 
                   'ינואר-מרס', 'אפריל-יוני', 'יולי-ספטמבר', 'אוקטובר-דצמבר']
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    print(f"Error: Missing required columns: {missing_columns}")
    exit(1)

# Step 1: Standardize the 'מטבע' column and adjust monetary values
# Define monetary columns to adjust
monetary_columns = ['ממוצע שנתי', 'ינואר-מרס', 'אפריל-יוני', 'יולי-ספטמבר', 'אוקטובר-דצמבר']

try:
    # Convert monetary values where 'מטבע' is 'אלפי שקלים חדשים' by multiplying by 1000
    mask = df['מטבע'] == 'אלפי שקלים חדשים'
    for col in monetary_columns:
        df.loc[mask, col] = df.loc[mask, col] * 1000
    
    # Update all 'מטבע' entries to 'שקלים חדשים'
    df['מטבע'] = 'שקלים חדשים'
    print("Standardized 'מטבע' to 'שקלים חדשים' and adjusted monetary values")
except Exception as e:
    print(f"Error during currency standardization: {e}")
    exit(1)

# Function to separate area and room number
def separate_area_room(value):
    """
    Separates the 'אזור וחדרים בדירה' column into 'אזור' (area) and 'חדרים בדירה' (room number).
    
    Args:
        value (str): The string value from the 'אזור וחדרים בדירה' column.
    
    Returns:
        tuple: (area, room_number) where area is the cleaned area name and room_number is the room range or 'הכל'.
    """
    if pd.isna(value):
        return None, None  # Handle missing values
    
    value = str(value).strip()  # Convert to string and remove leading/trailing spaces
    
    # Pattern 1: Simple area names (e.g., 'ירושלים')
    if '(' not in value and '-' not in value:
        return value, 'הכל'
    
    # Pattern 2: Room number ranges with area names (e.g., '2-1.5 (ירושלים)')
    match = re.match(r'([\d.-]+)\s*\(([^)]+)\)', value)
    if match:
        room_range, area = match.groups()
        # Remove any code (e.g., 'תל אביב - 5000') from the area
        area = re.sub(r'\s*-\s*\d+', '', area).strip()
        return area, room_range
    
    # Pattern 3: Area names with redundant codes (e.g., 'תל אביב - 5000')
    match = re.match(r'([^()]+?)\s*-\s*\d+', value)
    if match:
        area = match.group(1).strip()
        return area, 'הכל'
    
    # Pattern 4: Room number ranges with area names and codes (e.g., '1-2 (תל אביב - 5000)')
    match = re.match(r'([\d.-]+)\s*\(([^)]+)\)', value)
    if match:
        room_range, area_with_code = match.groups()
        # Remove the code from the area
        area = re.sub(r'\s*-\s*\d+', '', area_with_code).strip()
        return area, room_range
    
    # Default case: If no pattern matches, return the original value and 'הכל'
    return value, 'הכל'

# Apply the function to create 'אזור' and 'חדרים בדירה' columns
try:
    df[['אזור', 'חדרים בדירה']] = df['אזור וחדרים בדירה'].apply(lambda x: pd.Series(separate_area_room(x)))
    print("Successfully separated 'אזור וחדרים בדירה' into 'אזור' and 'חדרים בדירה'")
except Exception as e:
    print(f"Error during column separation: {e}")
    exit(1)

# Step 2: Replace "סך הכל" with "כולם" in the 'אזור' column
try:
    df['אזור'] = df['אזור'].replace('סך הכל', 'כולם')
    print('Replaced "סך הכל" with "כולם" in the "אזור" column')
except Exception as e:
    print(f"Error during replacement of 'סך הכל': {e}")
    exit(1)

# Step 3: Update "ממוצע שנתי" with the average of the four quarterly columns
quarterly_columns = ['ינואר-מרס', 'אפריל-יוני', 'יולי-ספטמבר', 'אוקטובר-דצמבר']
annual_avg_column = 'ממוצע שנתי'

try:
    # Ensure quarterly columns are numeric; convert if necessary
    for col in quarterly_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')  # Convert to numeric, set invalid values to NaN
    
    # Calculate the mean of the quarterly columns for each row
    df[annual_avg_column] = df[quarterly_columns].mean(axis=1)
    print('Updated "ממוצע שנתי" with the average of quarterly columns')
except Exception as e:
    print(f"Error calculating annual average: {e}")
    exit(1)

# Save the updated DataFrame to a new Excel file
try:
    output_path = 'preprocessed_apt_prices.xlsx'  # Replace with your desired output path
    df.to_excel(output_path, index=False, engine='openpyxl')
    print(f"Processed data saved to '{output_path}'")
except Exception as e:
    print(f"Error saving file: {e}")
    exit(1)