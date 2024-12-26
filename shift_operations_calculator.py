class ShiftOperationsCalculator:
    """
    A class to calculate historical average time and operations per shift
    for operators, styles, and operations.
    """

    def calculate_historical_average_time(self, df):
        """
        Calculate the average time required to complete each operation for each style.
        """
        # Ensure we are working on a copy of the DataFrame
        df = df.copy()

        # Calculate actual time per unit
        df['Actual_Time_per_Unit'] = df['ODPI_Actual_Time'] / df['ODPI_Quantity']

        # Group by style and operation to calculate averages
        historical_avg = df.groupby(['ODPI_ST_Description', 'ODPI_PC_Description']).agg(
            Average_Actual_Time_per_Unit=('Actual_Time_per_Unit', 'mean'),
            Standard_Time=('ODPI_OC_Standard_Time', 'mean')
        ).reset_index()

        return historical_avg

    def operations_per_shift(self, historical_avg):
        """
        Calculate the number of operations an operator can perform in a standard 8-hour shift (28800 seconds).
        """
        shift_duration = 8 * 60 * 60  # Standard shift duration in seconds

        # Ensure a copy to avoid modifying the original DataFrame
        historical_avg = historical_avg.copy()

        # Calculate operations per shift
        historical_avg['Operations_per_Shift_Standard'] = shift_duration / historical_avg['Standard_Time']
        historical_avg['Operations_per_Shift_Actual'] = shift_duration / historical_avg['Average_Actual_Time_per_Unit']

        return historical_avg

    def calculate_operator_avg_time(self, df, operators):
        """
        Calculate the average time each input operator takes to complete specific operations for each style.

        Args:
            df (pd.DataFrame): The input dataframe containing operator data.
            operators (list): List of input operator IDs.

        Returns:
            pd.DataFrame: A table showing average times for input operators.
        """
        # Ensure we are working on a copy of the DataFrame
        df = df.copy()

        # Calculate actual time per unit
        df['Actual_Time_per_Unit'] = df['ODPI_Actual_Time'] / df['ODPI_Quantity']

        # Filter data for input operators
        operator_df = df[df['ODPI_EM_Key'].isin(operators)]

        # Calculate average actual time per unit for each operator, style, and operation
        operator_avg = operator_df.groupby(['ODPI_EM_Key', 'ODPI_ST_Description', 'ODPI_PC_Description']).agg(
            Average_Actual_Time_per_Unit=('Actual_Time_per_Unit', 'mean'),
            Total_Quantity=('ODPI_Quantity', 'sum')
        ).reset_index()

        return operator_avg
