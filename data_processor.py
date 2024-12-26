import pandas as pd
import os

class DataProcessor:
    """
    A class to handle data loading and preprocessing for the Operator Allocation System.
    """

    def __init__(self, file_path):
        """
        Initialize the DataProcessor with the file path.

        Args:
            file_path (str): Path to the input dataset (Excel or CSV).
        """
        self.file_path = file_path

    def load_data(self):
        """
        Load the dataset into a Pandas DataFrame.
        Supports both CSV and Excel files.

        Returns:
            pd.DataFrame: Loaded dataset.
        """
        file_extension = os.path.splitext(self.file_path)[1].lower()
        if file_extension == '.csv':
            df = pd.read_csv(self.file_path, parse_dates=['ODPI_Date'])
        elif file_extension in ['.xls', '.xlsx']:
            df = pd.read_excel(self.file_path, parse_dates=['ODPI_Date'])
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        return self.preprocess_data(df)

    @staticmethod
    def preprocess_data(df):
        """
        Preprocess the dataset: clean, convert types, and handle missing values.

        Args:
            df (pd.DataFrame): Raw input dataset.

        Returns:
            pd.DataFrame: Preprocessed dataset.
        """
        # Strip whitespace from relevant columns
        df['ODPI_ST_Description'] = df['ODPI_ST_Description'].str.strip()
        df['ODPI_PC_Description'] = df['ODPI_PC_Description'].str.strip()

        # Ensure numeric columns are properly converted
        df['ODPI_OC_Standard_Time'] = pd.to_numeric(df['ODPI_OC_Standard_Time'], errors='coerce')
        df['ODPI_Quantity'] = pd.to_numeric(df['ODPI_Quantity'], errors='coerce')
        df['ODPI_Actual_Time'] = pd.to_numeric(df['ODPI_Actual_Time'], errors='coerce')

        # Ensure non-numeric columns are explicitly cast to strings
        df['ODPI_EM_LastName'] = df['ODPI_EM_LastName'].astype(str)
        df['ODPI_ODP_Shift'] = df['ODPI_ODP_Shift'].astype(str)

        # Drop rows with missing critical values
        df.dropna(subset=['ODPI_OC_Standard_Time', 'ODPI_Quantity', 'ODPI_Actual_Time'], inplace=True)

        return df
