import pandas as pd
import re
from sklearn.linear_model import LinearRegression

def main():
    try:
        # Load rent data
        rent_file = 'Data/Before preprocessing/rent_prices.xlsx'
        df = pd.read_excel(rent_file, engine='openpyxl')
        print(f"Loaded rent data from: {rent_file}")

        # =============================================================
        # Step 1: Preprocess rent data
        # =============================================================
        # Separate area and room information
        area_room_col = next((col for col in df.columns if 'אזור' in str(col) and 'חדרים' in str(col)), None)
        
        if area_room_col:
            # Define function to separate area and room columns
            def separate_area_room(value):
                value = str(value).strip()
                if '(' in value and ')' in value:
                    match = re.match(r'([\d.-]+)\s*\(([^)]+)\)', value)
                    if match:
                        rooms, area = match.groups()
                        return area.strip(), rooms.strip()
                return value, 'הכל'

            # Apply separation and assign to new columns
            df[['אזור', 'חדרים בדירה']] = df[area_room_col].apply(
                lambda x: pd.Series(separate_area_room(x))
            )

            # Clean up area names by removing numerical codes
            def clean_area_name(area):
                # Remove patterns like "region - code"
                if " - " in area:
                    return area.split(" - ")[0].strip()
                # Handle other potential formats
                return re.sub(r'\s*\d+\s*$', '', area).strip()

            # Apply the cleaning function to the area column
            df['אזור'] = df['אזור'].apply(clean_area_name)
            print(f"Cleaned up region names by removing numerical codes")

            # Standardize room ranges
            def fix_room_order(value):
                numbers = sorted([int(float(n)) for n in re.findall(r'\d+\.?\d*', str(value))])
                return f"{numbers[0]}-{numbers[1]}" if len(numbers) == 2 else value
            
            df['חדרים בדירה'] = df['חדרים בדירה'].apply(fix_room_order)
            df['אזור'] = df['אזור'].replace('סך הכל', 'כולם')
            
            # Update annual averages from quarterly data
            quarterly_cols = [col for col in df.columns if any(m in str(col) for m in ['ינואר', 'אפריל', 'יולי', 'אוקטובר'])]
            annual_col = next((col for col in df.columns if 'ממוצע' in str(col) or 'שנתי' in str(col)), None)
            
            if quarterly_cols and annual_col:
                df[quarterly_cols] = df[quarterly_cols].apply(pd.to_numeric, errors='coerce')
                df[annual_col] = df[quarterly_cols].mean(axis=1)

        # =============================================================
        # Step 2: Predict missing pre-1998 rents
        # =============================================================
        # Load apartment price data
        apt_file = 'preprocessed_apt_prices.xlsx'
        apt_df = pd.read_excel(apt_file, engine='openpyxl')
        print(f"Loaded apartment prices from: {apt_file}")

        # Create a complete grid of years, areas, and room types
        unique_combos = df[['אזור', 'חדרים בדירה']].drop_duplicates()
        min_year = 1986
        max_year = df['שנה'].max()
        all_years = pd.DataFrame({'שנה': range(min_year, max_year + 1)})
        full_grid = pd.merge(unique_combos.assign(key=1), all_years.assign(key=1), on='key').drop('key', axis=1)

        # Merge with apartment price data and rename price column
        full_data = pd.merge(
            full_grid,
            apt_df[['שנה', 'אזור', 'חדרים בדירה', 'ממוצע שנתי']],
            on=['שנה', 'אזור', 'חדרים בדירה'],
            how='left'
        ).rename(columns={'ממוצע שנתי': 'ממוצע שנתי_price'})

        # Merge with rent data
        full_data = pd.merge(
            full_data,
            df,
            on=['שנה', 'אזור', 'חדרים בדירה'],
            how='left'
        )

        # Identify the rent column
        rent_col = next(col for col in df.columns if 'ממוצע' in col or 'שנתי' in col)

        # Calculate rent ratios for existing data
        full_data['rent_ratio'] = full_data[rent_col] / full_data['ממוצע שנתי_price']

        # Train model on post-1998 data where ratios are available
        valid_data = full_data[(full_data['שנה'] >= 1998) & (full_data['rent_ratio'].notna())]
        if not valid_data.empty:
            model = LinearRegression()
            model.fit(valid_data[['שנה']], valid_data['rent_ratio'])
            
            # Predict pre-1998 rents where prices exist but rents are missing
            pre_1998 = full_data[
                (full_data['שנה'] < 1998) & 
                (full_data['ממוצע שנתי_price'].notna()) & 
                (full_data[rent_col].isna())
            ].copy()
            pre_1998[rent_col] = pre_1998['ממוצע שנתי_price'] * model.predict(pre_1998[['שנה']])
            
            # Combine predicted pre-1998 data with actual post-1998 data
            final_df = pd.concat([
                pre_1998[df.columns],
                df[df['שנה'] >= 1998]
            ], ignore_index=True).sort_values('שנה')
            
            print(f"Added {len(pre_1998)} pre-1998 records")
        else:
            final_df = df
            print("No predictions made - insufficient training data")

        # =============================================================
        # Step 3: Save final data
        # =============================================================
        output_file = 'preprocessed_rent_prices.xlsx'
        final_df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"Saved complete data to: {output_file}")
        print("Process completed successfully")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        if 'full_data' in locals():
            print("Debug Info - Columns:", full_data.columns.tolist())
            print("Debug Info - Sample Data:\n", full_data.head())
        exit(1)

if __name__ == "__main__":
    main()