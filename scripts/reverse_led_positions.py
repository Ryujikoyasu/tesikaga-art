import os
import glob
import csv

def reverse_csv_files():
    """
    Finds all led_positions_*.csv files in ../assets/data/ and reverses the order
    of their rows, keeping the header intact.
    """
    try:
        # Construct the path to the data directory relative to the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        data_dir = os.path.join(project_root, "assets", "data")
        
        # Find all matching CSV files
        search_pattern = os.path.join(data_dir, "led_positions_*.csv")
        csv_files = glob.glob(search_pattern)
        
        if not csv_files:
            print(f"No CSV files found matching the pattern: {search_pattern}")
            return

        print(f"Found {len(csv_files)} files to process...")

        for file_path in csv_files:
            try:
                with open(file_path, 'r', newline='') as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    data_rows = list(reader)
                
                # Reverse the data rows
                data_rows.reverse()
                
                # Write the header and reversed data back to the same file
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(data_rows)
                    
                print(f"Successfully reversed: {os.path.basename(file_path)}")

            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                
        print("\nAll files processed.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    reverse_csv_files()
