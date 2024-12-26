import numpy as np

class EfficiencyCalculator:
    """
    A class to calculate efficiencies, categorize operators, and identify bottlenecks in production.
    """

    @staticmethod
    def calculate_efficiency(df):
        """
        Calculate efficiency for the given dataset.
        """
        if 'ODPI_OC_Standard_Time' not in df.columns:
            raise KeyError("The required column 'ODPI_OC_Standard_Time' is missing from the dataset.")

        # Calculate mean standard time and total standard time for efficiency
        df['Mean_Standard_Time'] = df.groupby(['ODPI_ST_Description', 'ODPI_PC_Description'])[
            'ODPI_OC_Standard_Time'
        ].transform('mean')
        df['Total_Standard_Time_sec'] = df['Mean_Standard_Time'] * df['ODPI_Quantity']

        # Calculate efficiency
        df['Efficiency'] = (df['Total_Standard_Time_sec'] / df['ODPI_Actual_Time']) * 100

        # Filter out unrealistic efficiency values
        df = df[(df['Efficiency'] >= 5) & (df['Efficiency'] <= 200)]
        return df

    @staticmethod
    def aggregate_operator_data_grouped(df):
        """
        Aggregate operator data for categorized output, including days worked, operation frequency, and machine frequency.
        """
        if not {'ODPI_ST_Description', 'ODPI_PC_Description', 'ODPI_EM_Key', 'Efficiency', 'ODPI_Quantity', 'ODPI_Date', 'ODPI_MC_Type'}.issubset(df.columns):
            raise KeyError("Required columns are missing from the dataset for aggregation.")

        # Group by style, operation, and operator to calculate averages and sums
        grouped = df.groupby(['ODPI_ST_Description', 'ODPI_PC_Description', 'ODPI_EM_Key']).agg(
            Average_Efficiency=('Efficiency', 'mean'),
            Sum_Quantity=('ODPI_Quantity', 'sum'),
            Standard_Time=('ODPI_OC_Standard_Time', 'mean'),  # Include standard time for future usage
            Operation_Frequency=('ODPI_PC_Description', 'count')  # Frequency of operator performing this operation
        ).reset_index()

        # Calculate machine frequency
        machine_frequency = df.groupby(['ODPI_EM_Key', 'ODPI_MC_Type']).size().reset_index(name='Machine_Frequency')
        max_machine_frequency = machine_frequency.groupby('ODPI_EM_Key')['Machine_Frequency'].max()
        grouped = grouped.merge(max_machine_frequency.rename("Machine_Frequency"), on="ODPI_EM_Key", how="left")

        # Add days worked for each operator
        days_worked = df.groupby('ODPI_EM_Key')['ODPI_Date'].nunique()
        grouped = grouped.merge(days_worked.rename("Days_Worked"), on="ODPI_EM_Key", how="left")

        return grouped

    @staticmethod
    def categorize_with_grouped_averages(grouped_df, days_threshold=30):
        """
        Categorize operators using grouped averages, operation frequency, machine frequency, and days worked.
        """
        if not {'Average_Efficiency', 'Sum_Quantity', 'Days_Worked', 'Operation_Frequency', 'Machine_Frequency'}.issubset(grouped_df.columns):
            raise KeyError("Required columns are missing from the grouped data for categorization.")

        # Calculate mean and standard deviation for efficiency
        grouped_df['Efficiency_Mean'] = grouped_df.groupby(['ODPI_ST_Description', 'ODPI_PC_Description'])[
            'Average_Efficiency'
        ].transform('mean')
        grouped_df['Efficiency_Std'] = grouped_df.groupby(['ODPI_ST_Description', 'ODPI_PC_Description'])[
            'Average_Efficiency'
        ].transform('std')

        # Categorize efficiency
        grouped_df['Efficiency_Category'] = np.where(
            grouped_df['Average_Efficiency'] > (grouped_df['Efficiency_Mean'] + grouped_df['Efficiency_Std']),
            'High Performer',
            np.where(
                grouped_df['Average_Efficiency'] > grouped_df['Efficiency_Mean'],
                'Above Average',
                'Average'
            )
        )

        # Categorize experience
        grouped_df['Experience_Category'] = np.where(
            grouped_df['Days_Worked'] > days_threshold, 'Experienced', 'Fresher'
        )

        return grouped_df

    @staticmethod
    def calculate_operator_weightage(categorized_df):
        """
        Calculate weightage for each operator based on efficiency, quantity, experience, operation frequency, and machine frequency.

        Args:
            categorized_df (pd.DataFrame): Dataframe with categorized operators.

        Returns:
            pd.DataFrame: Updated dataframe with operator weightage.
        """
        if not {'Average_Efficiency', 'Sum_Quantity', 'Days_Worked', 'Operation_Frequency', 'Machine_Frequency'}.issubset(categorized_df.columns):
            raise KeyError("Required columns are missing from the categorized data for weightage calculation.")

        # Calculate base weightage with more weightage given to `Operation_Frequency` and `Machine_Frequency`
        categorized_df['Base_Weightage'] = (
            (categorized_df['Average_Efficiency'] / categorized_df['Average_Efficiency'].max()) * 0.2 +
            (categorized_df['Sum_Quantity'] / categorized_df['Sum_Quantity'].max()) * 0.2 +
            (categorized_df['Days_Worked'] / categorized_df['Days_Worked'].max()) * 0.1 +
            (categorized_df['Operation_Frequency'] / categorized_df['Operation_Frequency'].max()) * 0.25 +
            (categorized_df['Machine_Frequency'] / categorized_df['Machine_Frequency'].max()) * 0.25
        )

        # Normalize weightage
        categorized_df['Normalized_Weightage'] = categorized_df['Base_Weightage'] / categorized_df['Base_Weightage'].sum()
        return categorized_df

    @staticmethod
    def identify_bottlenecks(df):
        """
        Identify bottleneck operations for each style.

        Args:
            df (pd.DataFrame): Dataset containing efficiency data.

        Returns:
            dict: Bottleneck operations for each style.
        """
        if not {'ODPI_ST_Description', 'ODPI_PC_Description', 'Efficiency'}.issubset(df.columns):
            raise KeyError("Required columns are missing from the dataset for bottleneck identification.")

        bottlenecks = {}
        for style in df['ODPI_ST_Description'].unique():
            style_data = df[df['ODPI_ST_Description'] == style]
            avg_efficiency = style_data.groupby('ODPI_PC_Description')['Efficiency'].mean()

            # Identify operations with the lowest efficiency as bottlenecks
            bottlenecks[style] = avg_efficiency.nsmallest(3).index.tolist()
        return bottlenecks
