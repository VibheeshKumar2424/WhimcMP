import streamlit as st
import pandas as pd
from datetime import datetime
from collections import Counter
import hashlib
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import time

# Set page config
st.set_page_config(
    page_title="Data Validator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------ Simple CSS ------------------
st.markdown("""
<style>
    /* Clean styling */
    .main-header {
        background: #1E88E5;
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #ddd;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    .stButton > button {
        background: #1E88E5;
        color: white;
        border: none;
        padding: 0.5rem 1.5rem;
        border-radius: 5px;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background: #1976D2;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ Utility Functions (UNCHANGED) ------------------

def calculate_checksum(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

def validate_date(value):
    formats = ["%d/%m/%Y", "%m-%d-%Y"]
    for fmt in formats:
        try:
            datetime.strptime(str(value), fmt)
            return True
        except:
            pass
    return False

def validate_row(row, seen_ids):
    errors = []

    # order_id
    if pd.isna(row.get("order_id")):
        errors.append("Missing order_id")
    else:
        if row["order_id"] in seen_ids:
            errors.append("Duplicate order_id")
        seen_ids.add(row["order_id"])

    # item
    if pd.isna(row.get("item")) or str(row.get("item")).strip() == "":
        errors.append("Missing item")

    # date
    if pd.isna(row.get("date")) or not validate_date(row["date"]):
        errors.append("Invalid date (dd/mm/yyyy or mm-dd-yyyy)")

    # quantity
    try:
        qty = int(row.get("quantity"))
        if qty < 0:
            errors.append("Negative quantity")
    except:
        errors.append("Invalid quantity")

    # price
    try:
        price = float(row.get("price"))
        if price < 0:
            errors.append("Negative price")
    except:
        errors.append("Invalid price")

    if errors:
        return "Invalid", "; ".join(errors)
    return "Valid", "No errors"

# ------------------ Sidebar ------------------

with st.sidebar:
    st.title("📊 Data Validator")
    st.markdown("---")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload CSV/Excel File",
        type=["csv", "xlsx"],
        help="Upload file with columns: order_id, date, item, quantity, price"
    )
    
    if uploaded_file:
        st.markdown("---")
        st.markdown("**File Info:**")
        st.text(f"Name: {uploaded_file.name}")
        st.text(f"Type: {uploaded_file.type}")
        
        # Navigation
        st.markdown("---")
        st.markdown("**Navigation**")
        page = st.radio(
            "Go to:",
            ["📋 Preview", "📊 Dashboard", "❗ Errors", "⬇️ Export"],
            label_visibility="collapsed"
        )
    else:
        page = None

# ------------------ Main Content ------------------

if uploaded_file:
    # Read file
    file_bytes = uploaded_file.getvalue()
    checksum = calculate_checksum(file_bytes)

    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Failed to read file: {e}")
        st.stop()

    # Check required columns
    required_cols = ["order_id", "date", "item", "quantity", "price"]
    if not all(col in df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df.columns]
        st.error(f"Missing columns: {', '.join(missing)}")
        st.stop()

    # Validation
    st.info("🔄 Validating data...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    seen_ids = set()
    statuses, messages = [], []
    
    for i, (_, row) in enumerate(df.iterrows()):
        status, msg = validate_row(row, seen_ids)
        statuses.append(status)
        messages.append(msg)
        progress = (i + 1) / len(df)
        progress_bar.progress(progress)
        status_text.text(f"Processing: {i + 1}/{len(df)} rows")
    
    progress_bar.empty()
    status_text.text("✅ Validation complete!")
    
    df["status"] = statuses
    df["error_message"] = messages

    # Calculate stats
    total = len(df)
    valid = (df["status"] == "Valid").sum()
    invalid = (df["status"] == "Invalid").sum()
    validation_rate = (valid / total * 100) if total > 0 else 0

    # Update sidebar info
    with st.sidebar:
        st.markdown("---")
        st.markdown("**Validation Stats**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", total)
            st.metric("Valid", valid)
        with col2:
            st.metric("Invalid", invalid)
            st.metric("Rate", f"{validation_rate:.1f}%")

    # ------------------ PAGE 1: Preview ------------------
    if page == "📋 Preview":
        st.markdown('<div class="main-header">', unsafe_allow_html=True)
        st.markdown("## 📋 Data Preview")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Rows", total)
        col2.metric("Valid", valid)
        col3.metric("Invalid", invalid)
        col4.metric("Success Rate", f"{validation_rate:.1f}%")
        
        # Filters
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            filter_option = st.selectbox(
                "Show:",
                ["All rows", "Valid only", "Invalid only"]
            )
        with col2:
            rows_to_show = st.slider("Rows to display", 10, 100, 20)
        
        # Apply filter
        if filter_option == "Valid only":
            preview_df = df[df["status"] == "Valid"]
        elif filter_option == "Invalid only":
            preview_df = df[df["status"] == "Invalid"]
        else:
            preview_df = df
        
        # Display data - FIXED THE ERROR HERE
        st.dataframe(
            preview_df.head(rows_to_show),
            use_container_width=True,
            height=400
        )
        
        # Row details
        if not preview_df.empty:
            st.markdown("---")
            st.markdown("### 🔍 Row Details")
            selected_index = st.selectbox(
                "Select row to inspect:",
                range(len(preview_df.head(20))),
                format_func=lambda x: f"Row {x+1}"
            )
            
            if 0 <= selected_index < len(preview_df):
                row_data = preview_df.iloc[selected_index]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Data:**")
                    for col in required_cols:
                        st.text(f"{col}: {row_data[col]}")
                with col2:
                    st.write("**Status:**")
                    if row_data["status"] == "Valid":
                        st.success("✅ Valid")
                    else:
                        st.error(f"❌ {row_data['error_message']}")

    # ------------------ PAGE 2: Dashboard ------------------
    elif page == "📊 Dashboard":
        st.markdown('<div class="main-header">', unsafe_allow_html=True)
        st.markdown("## 📊 Analytics Dashboard")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Data", total)
        with col2:
            st.metric("✅ Clean Data", valid, f"{validation_rate:.1f}%")
        with col3:
            st.metric("❌ Issues Found", invalid)
        
        # Charts in tabs
        tab1, tab2 = st.tabs(["Validation Overview", "Error Analysis"])
        
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart
                fig = px.pie(
                    names=['Valid', 'Invalid'],
                    values=[valid, invalid],
                    title="Data Quality",
                    color=['Valid', 'Invalid'],
                    color_discrete_map={'Valid': '#00C853', 'Invalid': '#FF5252'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Bar chart
                fig = go.Figure(data=[
                    go.Bar(
                        name='Valid',
                        x=['Status'],
                        y=[valid],
                        marker_color='#00C853'
                    ),
                    go.Bar(
                        name='Invalid',
                        x=['Status'],
                        y=[invalid],
                        marker_color='#FF5252'
                    )
                ])
                fig.update_layout(title="Validation Results", barmode='stack')
                st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            # Error analysis
            error_list = []
            for msg in df[df["status"] == "Invalid"]["error_message"]:
                error_list.extend(msg.split("; "))
            
            if error_list:
                error_counts = Counter(error_list)
                error_df = pd.DataFrame({
                    'Error': list(error_counts.keys()),
                    'Count': list(error_counts.values())
                }).sort_values('Count', ascending=False)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    fig = px.bar(
                        error_df,
                        x='Error',
                        y='Count',
                        title="Error Types",
                        color='Count',
                        color_continuous_scale='Reds'
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.dataframe(error_df, use_container_width=True)
            else:
                st.success("🎉 No errors found!")
        
        # Data summary
        st.markdown("---")
        st.markdown("### 📈 Data Summary")
        
        summary_cols = ['quantity', 'price']
        for col in summary_cols:
            if col in df.columns:
                try:
                    numeric_data = pd.to_numeric(df[col], errors='coerce')
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric(f"{col} - Mean", f"{numeric_data.mean():.2f}")
                    col2.metric(f"{col} - Median", f"{numeric_data.median():.2f}")
                    col3.metric(f"{col} - Min", f"{numeric_data.min():.2f}")
                    col4.metric(f"{col} - Max", f"{numeric_data.max():.2f}")
                except:
                    pass

    # ------------------ PAGE 3: Errors ------------------
    elif page == "❗ Errors":
        st.markdown('<div class="main-header">', unsafe_allow_html=True)
        st.markdown("## ❌ Error Analysis")
        st.markdown("</div>", unsafe_allow_html=True)
        
        invalid_df = df[df["status"] == "Invalid"]
        
        if invalid_df.empty:
            st.success("✅ All data is valid! No errors found.")
        else:
            # Error summary
            st.metric("Total Errors Found", len(invalid_df))
            
            # Error type filter
            all_errors = []
            for msg in invalid_df['error_message']:
                all_errors.extend(msg.split('; '))
            
            unique_errors = sorted(set(all_errors))
            
            selected_errors = st.multiselect(
                "Filter by error type:",
                options=unique_errors,
                default=unique_errors[:2] if len(unique_errors) > 1 else unique_errors
            )
            
            # Apply filter
            if selected_errors:
                filtered_df = invalid_df[
                    invalid_df['error_message'].apply(
                        lambda x: any(err in x for err in selected_errors)
                    )
                ]
            else:
                filtered_df = invalid_df
            
            # Display errors
            st.dataframe(
                filtered_df,
                use_container_width=True,
                height=400
            )
            
            # Error details
            st.markdown("---")
            st.markdown("### 📋 Error Breakdown")
            
            error_details = []
            for _, row in filtered_df.iterrows():
                for error in row['error_message'].split('; '):
                    error_details.append({
                        'Row': _,
                        'Error': error
                    })
            
            if error_details:
                error_summary = pd.DataFrame(error_details)
                error_counts = error_summary['Error'].value_counts()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Error Frequency:**")
                    for error, count in error_counts.items():
                        st.write(f"• {error}: {count} times")
                with col2:
                    st.write("**Quick Fixes:**")
                    for error in error_counts.index[:3]:  # Top 3 errors
                        if "Missing" in error:
                            st.write(f"• Fill in missing values")
                        elif "Duplicate" in error:
                            st.write(f"• Remove duplicate entries")
                        elif "Invalid date" in error:
                            st.write(f"• Use dd/mm/yyyy or mm-dd-yyyy format")

    # ------------------ PAGE 4: Export ------------------
    elif page == "⬇️ Export":
        st.markdown('<div class="main-header">', unsafe_allow_html=True)
        st.markdown("## 📥 Export Results")
        st.markdown("</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📁 Export Options")
            
            # Format selection
            export_format = st.radio(
                "Select format:",
                ["CSV", "Excel"],
                horizontal=True
            )
            
            # What to export
            export_option = st.radio(
                "Export:",
                ["All data", "Valid only", "Invalid only"]
            )
            
            # Filter data
            if export_option == "Valid only":
                export_df = df[df["status"] == "Valid"]
            elif export_option == "Invalid only":
                export_df = df[df["status"] == "Invalid"]
            else:
                export_df = df
            
            # File name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"validated_data_{timestamp}"
            export_name = st.text_input("File name:", value=default_name)
        
        with col2:
            st.markdown("### 📊 Export Preview")
            
            # Preview
            st.dataframe(export_df.head(5), use_container_width=True)
            
            # Stats
            st.markdown("---")
            st.markdown("**Export Summary:**")
            st.write(f"• Rows: {len(export_df)}")
            st.write(f"• Columns: {len(export_df.columns)}")
            st.write(f"• Format: {export_format}")
        
        # Download buttons
        st.markdown("---")
        
        if export_format == "CSV":
            csv_data = export_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name=f"{export_name}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            # Excel export
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='Validated Data')
            
            st.download_button(
                label="📥 Download Excel",
                data=buffer.getvalue(),
                file_name=f"{export_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        # Additional options
        with st.expander("⚙️ Advanced Options"):
            col1, col2 = st.columns(2)
            with col1:
                include_status = st.checkbox("Include validation status", value=True)
                include_errors = st.checkbox("Include error messages", value=True)
            with col2:
                st.info("Note: Export may take a moment for large files")

else:
    # Landing page when no file is uploaded
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="main-header">', unsafe_allow_html=True)
        st.markdown("# 📊 Data Validator Tool")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Simple instructions
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🚀 How to Use:")
        st.markdown("""
        1. **Upload** your CSV/Excel file
        2. **Preview** your data
        3. **Analyze** validation results
        4. **Export** cleaned data
        """)
    
    with col2:
        st.markdown("### 📋 Requirements:")
        st.markdown("""
        Your file must include:
        - `order_id` (unique)
        - `date` (dd/mm/yyyy or mm-dd-yyyy)
        - `item` (text)
        - `quantity` (number)
        - `price` (number)
        """)
    
    st.markdown("---")
    
    # Quick tips
    with st.expander("💡 Tips for Best Results"):
        st.markdown("""
        - Ensure dates are in correct format
        - Check for duplicate order IDs
        - Verify all required fields are filled
        - Use consistent number formats
        - Save as CSV for best compatibility
        """)
    
    # Empty state visualization
    st.markdown("")
    col1, col2, col3 = st.columns(3)
    with col2:
        st.info("👈 Upload a file from the sidebar to get started!")