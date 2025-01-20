import numpy as np
import pandas as pd

class OperatorAllocator:
    """
    A class to dynamically allocate operators to operations for one or more styles based on 
    efficiency, historical frequency, and operation-specific requirements.
    """

    def __init__(self):
        """
        Initialize the allocator with a set to track assigned operators.
        """
        self.assigned_operators = set()  # To keep track of assigned operators

    def allocate_operators(self, categorized_df, df, operators, styles):
        """
        Main function to allocate operators to operations for each style.

        Args:
            categorized_df (pd.DataFrame): Dataframe with categorized operator data.
            df (pd.DataFrame): Original dataset with operator and operation details.
            operators (list): List of available operator IDs.
            styles (list): List of styles to allocate.
        
        Returns:
            dict: Allocation of operators to operations for each style.
        """
        allocation = {}
        
        # Calculate the total number of operations for each style
        style_operation_counts = (
            df[df['ODPI_ST_Description'].isin(styles)]
            .groupby('ODPI_ST_Description')['ODPI_PC_Description']
            .nunique()
            .reset_index()
            .rename(columns={'ODPI_PC_Description': 'Total_Operations'})
        )

        total_operations = style_operation_counts['Total_Operations'].sum()
        style_operation_counts['Operator_Allocation'] = np.ceil(
            (style_operation_counts['Total_Operations'] / total_operations) * len(operators)
        ).astype(int)

        for style in styles:
            allocation[style] = {}
            num_style_operators = style_operation_counts.loc[
                style_operation_counts['ODPI_ST_Description'] == style, 'Operator_Allocation'
            ].values[0]

            available_operators = operators[:num_style_operators]
            operators = operators[num_style_operators:]  # Remove assigned operators

            # Get operation time requirements, excluding "QUALITY CHECKING"
            operation_times = (
                df[(df['ODPI_ST_Description'] == style) & (df['ODPI_PC_Description'] != "QUALITY CHECK","QUALITY CHECKING)]
                .groupby('ODPI_PC_Description')['ODPI_OC_Standard_Time']
                .mean()
                .reset_index()
            )

            operation_times = operation_times.sort_values('ODPI_OC_Standard_Time', ascending=False)

            # Allocate operators to operations
            for _, operation_row in operation_times.iterrows():
                operation = operation_row['ODPI_PC_Description']
                operation_time = operation_row['ODPI_OC_Standard_Time']

                proportion = operation_time / operation_times['ODPI_OC_Standard_Time'].sum()
                num_operators = max(1, min(7, int(np.ceil(proportion * len(available_operators)))))

                assigned = self._assign_to_operation(
                    categorized_df,
                    operation,
                    style,
                    available_operators,
                    num_operators
                )
                allocation[style][operation] = assigned

            self._fill_empty_operations(allocation, operation_times, categorized_df, style, available_operators)

        self._ensure_no_empty_operations(allocation)
        return allocation

    def _assign_to_operation(self, categorized_df, operation, style, operators, num_operators):
        """
        Assign operators to a specific operation based on weightage and historical frequency.
        """
        eligible_operators = categorized_df[
            (categorized_df['ODPI_PC_Description'] == operation) &
            (categorized_df['ODPI_ST_Description'] == style) &
            (categorized_df['ODPI_EM_Key'].isin(operators)) &
            (~categorized_df['ODPI_EM_Key'].isin(self.assigned_operators))
        ].sort_values(['Operation_Frequency', 'Normalized_Weightage'], ascending=False)

        assigned = eligible_operators['ODPI_EM_Key'].head(num_operators).tolist()
        self.assigned_operators.update(assigned)
        return assigned

    def _fill_empty_operations(self, allocation, operation_times, categorized_df, style, operators):
        """
        Ensure that all operations are assigned operators, filling gaps if needed.
        """
        for _, operation_row in operation_times.iterrows():
            operation = operation_row['ODPI_PC_Description']
            if operation not in allocation[style] or not allocation[style][operation]:
                unskilled = self._get_unskilled_operators(categorized_df, operation, style, operators)
                if not unskilled.empty:
                    allocation[style][operation] = [unskilled['ODPI_EM_Key'].iloc[0]]
                    self.assigned_operators.add(unskilled['ODPI_EM_Key'].iloc[0])
                else:
                    for assigned_operation, assigned_operators in allocation[style].items():
                        if assigned_operators:
                            reallocated_operator = assigned_operators.pop(0)
                            allocation[style][operation] = [reallocated_operator]
                            self.assigned_operators.add(reallocated_operator)
                            break

    def _get_unskilled_operators(self, categorized_df, operation, style, operators):
        """
        Get operators who are not skilled but available for the operation and style.
        """
        return categorized_df[
            (categorized_df['ODPI_EM_Key'].isin(operators)) &
            (categorized_df['ODPI_EM_Key'].isin(self.assigned_operators) == False) &
            (~(
                (categorized_df['ODPI_PC_Description'] == operation) &
                (categorized_df['ODPI_ST_Description'] == style)
            ))
        ].sort_values('Normalized_Weightage', ascending=False)

    def _ensure_no_empty_operations(self, allocation):
        """
        Ensure that every operation has at least one operator assigned.
        """
        for style, operations in allocation.items():
            for operation, assigned_operators in operations.items():
                if not assigned_operators:
                    self._redistribute_operators(allocation, style, operation)

    def _redistribute_operators(self, allocation, style, operation):
        """
        Redistribute operators to ensure that every operation has at least one operator.
        """
        for assigned_operation, assigned_operators in allocation[style].items():
            if len(assigned_operators) > 1:
                reallocated_operator = assigned_operators.pop(0)
                allocation[style][operation] = [reallocated_operator]
                self.assigned_operators.add(reallocated_operator)
                break

    def calculate_achieved_efficiency(self, allocation, categorized_df):
        """
        Calculate the achieved efficiency based on the allocation.
        """
        achieved_efficiency = {}

        for style, operations in allocation.items():
            total_efficiency = 0
            total_operations = 0

            for operation, assigned_operators in operations.items():
                for operator in assigned_operators:
                    operator_efficiency = categorized_df[
                        (categorized_df['ODPI_EM_Key'] == operator) &
                        (categorized_df['ODPI_ST_Description'] == style) &
                        (categorized_df['ODPI_PC_Description'] == operation)
                    ]['Average_Efficiency']
                    if not operator_efficiency.empty:
                        total_efficiency += operator_efficiency.values[0]
                        total_operations += 1

            achieved_efficiency[style] = total_efficiency / total_operations if total_operations > 0 else 0

        return achieved_efficiency
