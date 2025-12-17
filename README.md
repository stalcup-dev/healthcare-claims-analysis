# Healthcare Claims Analysis Project

## Overview

Python-based analysis of synthetic healthcare claims data. Identifies top diagnoses by cost, monthly trends, and insights for healthcare domain.

## Files

- **Healthcare_Claims_Analysis.ipynb**: Main Jupyter notebook with code, visualization, and report. Contains 3 days of analysis:
  - Day 1: Data exploration and shape verification
  - Day 2: Data cleaning and core analysis with visualizations
  - Day 3: Reporting, insights, and demo preparation
- **claim_data.csv**: Synthetic dataset from Kaggle containing healthcare claims records
- **Healthcare_Claims_Analysis.pdf**: Exported report (generate by running the export cell in the notebook)

## How to Run

1. **Install dependencies:**
   ```bash
   pip install pandas numpy matplotlib jupyter
   ```

2. **Run notebook cells sequentially:**
   - Start from the top and execute cells in order
   - Each day builds on previous analysis
   - Visualizations will display inline

3. **Export to PDF (optional):**
   - Run the "Export to PDF" cell in the notebook to generate a shareable PDF report

## Key Learnings

- **EDA and Cleaning**: Data quality checks, outlier handling, and missing value treatment
- **Aggregation**: Grouping by diagnosis codes to extract cost insights and trends
- **Visualization**: Using bar and line plots for effective storytelling with data
- **Time-Series Analysis**: Monthly trend identification for healthcare forecasting
- **Domain Knowledge**: Understanding ICD codes, billed amounts, and insurance workflows

## Project Scope

Built as a 3-day structured project for portfolio demonstration and interview prep. Showcases healthcare analytics capabilities valuable in data analytics, business intelligence, and health tech roles.

## Technologies Used

- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical computing
- **Matplotlib**: Data visualization
- **Jupyter**: Interactive notebook environment

## Future Enhancements

- Add HIPAA compliance considerations for real data
- Scale analysis with SQL or Spark for larger datasets
- Integrate predictive modeling for cost forecasting
- Create interactive dashboards with Plotly or Tableau
