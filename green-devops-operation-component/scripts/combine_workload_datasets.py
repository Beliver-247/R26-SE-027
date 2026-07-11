"""
Combine multiple CSV workload datasets into a single clean dataset.
Part of Green DevOps Operation Phase system.
"""

import os
import pandas as pd
import logging
from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_column_mapping(df: pd.DataFrame) -> Optional[Tuple[str, str, str]]:
    """
    Dynamically identify timestamp, CPU, and memory columns.
    
    Args:
        df: DataFrame to inspect
        
    Returns:
        Tuple of (timestamp_col, cpu_col, memory_col) or None if not found
    """
    columns_lower = {col.lower(): col for col in df.columns}
    
    # Timestamp column patterns
    timestamp_col = None
    timestamp_patterns = ['timestamp', 'time', 'date', 'datetime', 'ts']
    for pattern in timestamp_patterns:
        # Check both exact matches and substring matches
        matching = [k for k in columns_lower.keys() if pattern in k.lower()]
        if matching:
            timestamp_col = columns_lower[matching[0]]
            break
    
    # CPU column patterns - prioritize CPU usage [%]
    cpu_col = None
    cpu_patterns = ['cpu usage [%]', 'cpu usage', 'cpu', 'processor', 'cpu_usage', 'cpu_util', 'cpu_utilization']
    for pattern in cpu_patterns:
        matching = [k for k in columns_lower.keys() if pattern.lower() in k.lower()]
        if matching:
            cpu_col = columns_lower[matching[0]]
            break
    
    # Memory column patterns - prioritize Memory usage [KB]
    memory_col = None
    memory_patterns = ['memory usage [kb]', 'memory usage', 'memory', 'mem', 'memory_usage', 'mem_util', 'memory_utilization', 'ram']
    for pattern in memory_patterns:
        matching = [k for k in columns_lower.keys() if pattern.lower() in k.lower()]
        if matching:
            memory_col = columns_lower[matching[0]]
            break
    
    if timestamp_col and cpu_col and memory_col:
        return timestamp_col, cpu_col, memory_col
    
    return None


def validate_numeric_column(col_data: pd.Series, col_name: str) -> bool:
    """
    Validate that column contains numeric data.
    
    Args:
        col_data: Column data
        col_name: Column name for logging
        
    Returns:
        True if column is numeric or can be converted
    """
    try:
        pd.to_numeric(col_data, errors='coerce')
        return True
    except Exception as e:
        logger.warning(f"Column {col_name} cannot be converted to numeric: {e}")
        return False


def load_and_process_file(
    file_path: Path,
    system_id: str
) -> Optional[pd.DataFrame]:
    """
    Load and process a single CSV file.
    
    Args:
        file_path: Path to CSV file
        system_id: System identifier (filename)
        
    Returns:
        Processed DataFrame or None if processing fails
    """
    try:
        # Try semicolon separator first (for fastStorage dataset), then default
        try:
            df = pd.read_csv(file_path, sep=';', dtype_backend='numpy_nullable')
        except:
            df = pd.read_csv(file_path, dtype_backend='numpy_nullable')
        
        # Clean column names: strip whitespace and tabs
        df.columns = df.columns.str.strip()
        
        # Skip empty files
        if df.empty:
            logger.warning(f"Skipping empty file: {file_path.name}")
            return None
        
        # Find column mapping
        mapping = find_column_mapping(df)
        if not mapping:
            logger.warning(f"Skipping {file_path.name}: Could not identify required columns")
            logger.debug(f"  Available columns: {df.columns.tolist()}")
            return None
        
        timestamp_col, cpu_col, memory_col = mapping
        
        # Validate numeric columns
        if not validate_numeric_column(df[cpu_col], cpu_col):
            logger.warning(f"Skipping {file_path.name}: CPU column not numeric")
            return None
        
        if not validate_numeric_column(df[memory_col], memory_col):
            logger.warning(f"Skipping {file_path.name}: Memory column not numeric")
            return None
        
        # Select and rename columns
        df_processed = df[[timestamp_col, cpu_col, memory_col]].copy()
        df_processed.columns = ['timestamp', 'cpu', 'memory']
        
        # Convert to numeric
        df_processed['cpu'] = pd.to_numeric(df_processed['cpu'], errors='coerce')
        df_processed['memory'] = pd.to_numeric(df_processed['memory'], errors='coerce')
        
        # Remove rows with NaN values in numeric columns
        df_processed = df_processed.dropna(subset=['cpu', 'memory'])
        
        # Add system_id
        df_processed['system_id'] = system_id
        
        # Convert timestamp to numeric if it's not already
        try:
            df_processed['timestamp'] = pd.to_numeric(
                df_processed['timestamp'],
                errors='coerce'
            )
        except Exception as e:
            logger.warning(f"Could not convert timestamp to numeric in {file_path.name}: {e}")
            return None
        
        # Remove rows with NaN timestamp
        df_processed = df_processed.dropna(subset=['timestamp'])
        
        if df_processed.empty:
            logger.warning(f"No valid data in {file_path.name} after processing")
            return None
        
        logger.info(f"Processed {file_path.name}: {len(df_processed)} records")
        return df_processed
        
    except Exception as e:
        logger.error(f"Error processing {file_path.name}: {e}")
        return None


def combine_datasets(
    input_folder: str,
    num_files: int = 25,
    output_path: str = None
) -> pd.DataFrame:
    """
    Combine multiple CSV workload datasets into a single dataset.
    
    Args:
        input_folder: Path to folder containing CSV files
        num_files: Number of CSV files to process (default 25)
        output_path: Path to save output CSV (optional)
        
    Returns:
        Combined DataFrame
    """
    input_path = Path(input_folder)
    
    if not input_path.exists():
        logger.error(f"Input folder not found: {input_folder}")
        raise FileNotFoundError(f"Input folder not found: {input_folder}")
    
    # Find all CSV files
    csv_files = sorted(input_path.glob('*.csv'), key=lambda x: int(x.stem))
    
    if not csv_files:
        logger.error(f"No CSV files found in {input_folder}")
        raise FileNotFoundError(f"No CSV files found in {input_folder}")
    
    # Limit to num_files
    csv_files = csv_files[:num_files]
    logger.info(f"Found {len(csv_files)} CSV files to process")
    
    # Process files
    dataframes = []
    processed_count = 0
    failed_files = []
    
    for idx, file_path in enumerate(csv_files, 1):
        logger.info(f"Processing file {idx}/{len(csv_files)}: {file_path.name}")
        
        df_processed = load_and_process_file(file_path, file_path.stem)
        
        if df_processed is not None:
            dataframes.append(df_processed)
            processed_count += 1
        else:
            failed_files.append(file_path.name)
    
    # Log summary
    logger.info(f"Processing complete: {processed_count}/{len(csv_files)} files processed successfully")
    
    if failed_files:
        logger.warning(f"Failed to process {len(failed_files)} files: {', '.join(failed_files)}")
    
    if not dataframes:
        logger.error("No data was successfully processed")
        raise ValueError("No data was successfully processed from any file")
    
    # Combine all dataframes
    logger.info("Combining all dataframes...")
    combined_df = pd.concat(dataframes, ignore_index=True)
    logger.info(f"Combined dataset shape: {combined_df.shape}")
    
    # Sort by timestamp
    logger.info("Sorting by timestamp...")
    combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
    
    # Verify no null values
    null_counts = combined_df.isnull().sum()
    if null_counts.sum() > 0:
        logger.warning(f"Found null values: {null_counts[null_counts > 0].to_dict()}")
        logger.info("Removing rows with null values...")
        combined_df = combined_df.dropna()
        logger.info(f"Dataset shape after removing nulls: {combined_df.shape}")
    
    # Verify column order
    combined_df = combined_df[['timestamp', 'cpu', 'memory', 'system_id']]
    
    logger.info(f"Final dataset info:")
    logger.info(f"  Shape: {combined_df.shape}")
    logger.info(f"  Columns: {combined_df.columns.tolist()}")
    logger.info(f"  Timestamp range: {combined_df['timestamp'].min()} - {combined_df['timestamp'].max()}")
    logger.info(f"  CPU range: {combined_df['cpu'].min():.2f} - {combined_df['cpu'].max():.2f}")
    logger.info(f"  Memory range: {combined_df['memory'].min():.2f} - {combined_df['memory'].max():.2f}")
    logger.info(f"  Unique systems: {combined_df['system_id'].nunique()}")
    
    # Save output if path provided
    if output_path:
        output_file = Path(output_path)
        output_dir = output_file.parent
        
        # Create output directory if not exists
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")
        
        # Save to CSV
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved combined dataset to: {output_file}")
        logger.info(f"File size: {output_file.stat().st_size / (1024*1024):.2f} MB")
    
    return combined_df


def main():
    """Main execution block."""
    # Configuration
    INPUT_FOLDER = r"D:\Research\Operation\green-devops-operation-component\data\public_datasets\fastStorage\2013-8"
    OUTPUT_PATH = r"D:\Research\Operation\green-devops-operation-component\data\processed\workload_data.csv"
    NUM_FILES = 25
    
    logger.info("=" * 80)
    logger.info("Starting workload dataset combination process...")
    logger.info("=" * 80)
    logger.info(f"Input folder: {INPUT_FOLDER}")
    logger.info(f"Number of files to process: {NUM_FILES}")
    logger.info(f"Output path: {OUTPUT_PATH}")
    logger.info("=" * 80)
    
    try:
        # Combine datasets
        combined_df = combine_datasets(
            input_folder=INPUT_FOLDER,
            num_files=NUM_FILES,
            output_path=OUTPUT_PATH
        )
        
        logger.info("=" * 80)
        logger.info("SUCCESS: Workload datasets combined successfully!")
        logger.info("=" * 80)
        
        # Display sample data
        logger.info("\nSample of combined dataset (first 10 rows):")
        logger.info("\n" + str(combined_df.head(10)))
        
        return combined_df
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"FAILED: {str(e)}")
        logger.error("=" * 80)
        raise


if __name__ == "__main__":
    result_df = main()
