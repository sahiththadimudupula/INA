import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from data_processor import DataProcessor
from efficiency_calculator import EfficiencyCalculator
from shift_operations_calculator import ShiftOperationsCalculator
from operator_allocator import OperatorAllocator
import io

# Page configuration
st.set_page_config(
    page_title="Operator Performance Analysis",
    layout="wide"
)

# Custom CSS for improved UI
st.markdown(
    """
    <style>
    body {
        font-family: Arial, sans-serif;
    }
    .main {
        font-family: Arial, sans-serif;
        font-size: 16px;
        line-height: 1.6;
    }
    h1, h2, h3 {
        color: #2E3B4E;
        font-weight: bold;
    }
    h1 {
        font-size: 28px;
    }
    h2 {
        font-size: 24px;
    }
    h3 {
        font-size: 20px;
    }
    p, label {
        font-size: 16px;
        color: #34495E;
    }
    .stButton>button {
        background-color: #007BFF;
        color: white;
        font-size: 16px;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
    }
    .stDownloadButton>button {
        background-color: #28A745;
        color: white;
        font-size: 16px;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
    }
    .stSidebar > div {
        font-size: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Title of the app
st.title("Operator Performance Analysis System")
st.markdown(
    """
    This system provides insights into operator efficiency, allocation, and overall performance for INA production lines. 
    It offers detailed reports, visualizations, and professional outputs tailored for industrial analysis.
    """
)

# Function 1: Dataset Selection
def select_dataset(datasets):
    st.sidebar.header("Dataset Selection")
    selected_dataset = st.sidebar.selectbox("Choose an INA Line dataset to analyze:", datasets)
    return selected_dataset

# Function 3: Style Selection
def select_styles(df):
    st.sidebar.header("Style Selection")
    if 'ODPI_ST_Description' in df.columns:
        # Exclude rows where the column has NaN values
        styles = df['ODPI_ST_Description'].dropna().unique()
        selected_styles = st.sidebar.multiselect(
            "Select styles from the available options:",
            options=styles,
        )
        return selected_styles
    else:
        st.sidebar.warning("Style descriptions not found in the dataset.")
        return []

# Function 2: Operator Selection
def select_operators(df):
    st.sidebar.header("Operator Selection")
    if 'ODPI_EM_Key' in df.columns and 'Operator_FullName' in df.columns:
        # Exclude rows where either column has NaN values
        df_filtered = df.dropna(subset=['ODPI_EM_Key', 'Operator_FullName'])
        df_filtered['Operator_Display'] = df_filtered['ODPI_EM_Key'].astype(str) + " - " + df_filtered['Operator_FullName']
        selected_display = st.sidebar.multiselect(
            "Select operators from the list below:",
            options=df_filtered['Operator_Display'].unique(),
        )
        selected_operators = df_filtered[df_filtered['Operator_Display'].isin(selected_display)][['ODPI_EM_Key', 'Operator_FullName']].drop_duplicates()
        return selected_operators
    else:
        st.sidebar.warning("Operator information not found in the dataset.")
        return pd.DataFrame(columns=['ODPI_EM_Key', 'Operator_FullName'])


# List of datasets
datasets = [f"ina_line{i}.csv" for i in range(1, 13)]

# Step 1: Dataset selection
file_path = select_dataset(datasets)

# Load dataset
st.subheader("Step 1: Loading INA Line")
processor = DataProcessor(file_path)
df = processor.load_data()
if df.empty:
    st.error("The uploaded INA Line is empty or could not be loaded correctly. Please check the file and try again.")
    st.stop()

# Display and download the full dataset
st.write("### INA Line Preview")
st.dataframe(df.head())
buffer = io.BytesIO()
df.to_csv(buffer, index=False)
buffer.seek(0)
st.download_button(
    label="Download Full INA Line (CSV)",
    data=buffer,
    file_name="full_dataset.csv",
    mime="text/csv"
)

# Step 3: Style selection
styles = select_styles(df)
if not styles:
    st.error("No styles selected. Please choose at least one style to proceed.")
    st.stop()

# Step 2: Operator selection
selected_operators = select_operators(df)
if selected_operators.empty:
    st.error("No operators selected. Please choose at least one operator to proceed.")
    st.stop()


# Step 4: Efficiency calculations
st.subheader("Step 4: Calculating Efficiencies")
calculator = EfficiencyCalculator()
df = calculator.calculate_efficiency(df)

# Filter data based on selected styles
df = df[df['ODPI_ST_Description'].isin(styles)]
if df.empty:
    st.error(f"No data is available for the selected styles: {styles}. Please adjust your selection.")
    st.stop()

# Visualization of Efficiency by Style
st.subheader("Efficiency Visualization by Style")
for style in styles:
    st.markdown(f"#### Efficiency for Style: {style}")
    fig, ax = plt.subplots(figsize=(16, 8))
    style_data = df[df['ODPI_ST_Description'] == style]
    if not style_data.empty:
        style_data['Month'] = style_data['ODPI_Date'].dt.to_period('M')
        sns.boxplot(
            data=style_data,
            x='ODPI_PC_Description',
            y='Efficiency',
            hue='Month',
            palette="pastel",
            showfliers=True,
            ax=ax
        )
        avg_efficiency = style_data['Efficiency'].mean()
        target_efficiency = 75
        ax.axhline(target_efficiency, color='black', linestyle='--', linewidth=2, label=f"Target Efficiency ({target_efficiency}%)")
        ax.axhline(avg_efficiency, color='red', linestyle='-', linewidth=2, label=f"Average Efficiency ({avg_efficiency:.2f}%)")
        ax.set_title(f"Efficiency for Style: {style}", fontsize=16)
        ax.set_xlabel("Process Description", fontsize=14)
        ax.set_ylabel("Efficiency (%)", fontsize=14)
        ax.tick_params(axis='x', rotation=45)
        ax.legend(title="Legend", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        st.pyplot(fig)
    else:
        st.warning(f"No efficiency data is available for the style: {style}")

# Grouping, Categorizing, and Calculating Weightage
st.subheader("Step 5: Grouping, Categorizing, and Weightage Calculation")
grouped_data = calculator.aggregate_operator_data_grouped(df)
categorized_data = calculator.categorize_with_grouped_averages(grouped_data, 30)
categorized_data = calculator.calculate_operator_weightage(categorized_data)
categorized_data = categorized_data.merge(df[['ODPI_EM_Key', 'Operator_FullName']].drop_duplicates(), on='ODPI_EM_Key', how='left')

# Display and download categorized data
st.write("### Categorized Data")
st.dataframe(categorized_data.head())
categorized_buffer = io.BytesIO()
categorized_data.to_csv(categorized_buffer, index=False)
categorized_buffer.seek(0)
st.download_button(
    label="Download Categorized Data (CSV)",
    data=categorized_buffer,
    file_name="categorized_data.csv",
    mime="text/csv"
)

# Step 6: Historical averages and operations per shift
st.subheader("Step 6: Historical Averages and Operations Analysis")
shift_calculator = ShiftOperationsCalculator()
historical_avg = shift_calculator.calculate_historical_average_time(df)
operations_per_shift = shift_calculator.operations_per_shift(historical_avg)

st.write("### Operations Summary")
st.dataframe(operations_per_shift.head())
operations_buffer = io.BytesIO()
operations_per_shift.to_csv(operations_buffer, index=False)
operations_buffer.seek(0)
st.download_button(
    label="Download Operations Data (CSV)",
    data=operations_buffer,
    file_name="operations_data.csv",
    mime="text/csv"
)

# Step 7: Operator Allocation
st.subheader("Step 7: Operator Allocation")
allocator = OperatorAllocator()
allocation = allocator.allocate_operators(categorized_data, df, selected_operators['ODPI_EM_Key'].tolist(), styles)

st.write("### Operator Allocation Summary")
for style, operations in allocation.items():
    st.write(f"#### Style: {style}")
    for operation, ops in operations.items():
        st.write(f"##### Operation: {operation}")
        operator_details = [
            f"- Name: {df.loc[df['ODPI_EM_Key'] == operator, 'Operator_FullName'].values[0]} (Key: {operator})"
            for operator in ops
        ]
        st.write("\n".join(operator_details))

# Prepare allocation report for download
allocation_report = []
for style, operations in allocation.items():
    for operation, ops in operations.items():
        for operator in ops:
            allocation_report.append({
                'Style': style,
                'Operation': operation,
                'Operator Key': operator,
                'Operator Name': df.loc[df['ODPI_EM_Key'] == operator, 'Operator_FullName'].values[0]
            })

allocation_df = pd.DataFrame(allocation_report)
st.write("### Operator Allocation Report")
st.dataframe(allocation_df.head())

allocation_buffer = io.BytesIO()
allocation_df.to_csv(allocation_buffer, index=False)
allocation_buffer.seek(0)
st.download_button(
    label="Download Allocation Report (CSV)",
    data=allocation_buffer,
    file_name="operator_allocation_report.csv",
    mime="text/csv"
)

st.success("Analysis complete! All reports are available for download.")

# Step 8: Calculate and Display Achieved Efficiency
st.subheader("Step 8: Achieved Efficiency")
achieved_efficiency = allocator.calculate_achieved_efficiency(allocation, categorized_data)

# Convert achieved efficiency to a DataFrame for display and download
efficiency_report = pd.DataFrame({
    'Style': list(achieved_efficiency.keys()),
    'Achieved Efficiency (%)': list(achieved_efficiency.values())
})

# Display the Achieved Efficiency Report
st.write("### Achieved Efficiency Report")
st.dataframe(efficiency_report.head())

# Add a download button for the Achieved Efficiency Report
efficiency_buffer = io.BytesIO()
efficiency_report.to_csv(efficiency_buffer, index=False)
efficiency_buffer.seek(0)
st.download_button(
    label="Download Achieved Efficiency Report (CSV)",
    data=efficiency_buffer,
    file_name="achieved_efficiency_report.csv",
    mime="text/csv"
)

st.success("Analysis complete! Achieved Efficiency Report is available for download.")
