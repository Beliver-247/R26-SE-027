"""
LSTM preprocessing pipeline for workload time-series data.
Transforms combined workload data into sequences suitable for LSTM training.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Tuple, Dict, List
from sklearn.preprocessing import MinMaxScaler
import pickle

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LSTMPreprocessor:
    """Preprocess workload data for LSTM model training."""
    
    def __init__(self, sequence_length: int = 12, test_split: float = 0.2):
        """
        Initialize preprocessor.
        
        Args:
            sequence_length: Number of timesteps in each sequence (default 12 = 6 minutes)
            test_split: Fraction of data for testing (default 0.2 = 20%)
        """
        self.sequence_length = sequence_length
        self.test_split = test_split
        self.scalers = {}
        self.feature_names = ['cpu', 'memory']
    
    def load_data(self, data_path: str) -> pd.DataFrame:
        """Load combined workload data."""
        if not Path(data_path).exists():
            logger.error(f"File not found: {data_path}")
            raise FileNotFoundError(f"File not found: {data_path}")
        
        logger.info(f"Loading data from: {data_path}")
        df = pd.read_csv(data_path)
        logger.info(f"Loaded {len(df)} records with columns: {list(df.columns)}")
        
        return df
    
    def normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize features using MinMaxScaler.
        
        Args:
            df: DataFrame with features to normalize
            
        Returns:
            DataFrame with normalized features
        """
        logger.info("Normalizing features...")
        df_normalized = df.copy()
        
        for feature in self.feature_names:
            scaler = MinMaxScaler(feature_range=(0, 1))
            df_normalized[feature] = scaler.fit_transform(df[[feature]])
            self.scalers[feature] = scaler
            logger.info(f"Normalized feature: {feature}")
        
        return df_normalized
    
    def create_sequences(self, data: np.ndarray, labels: np.ndarray = None) -> Tuple:
        """
        Create sequences for LSTM training.
        
        Args:
            data: Array of shape (n_samples, n_features)
            labels: Optional array of target values
            
        Returns:
            Tuple of (sequences, targets) if labels provided, else sequences
        """
        sequences = []
        targets = []
        
        for i in range(len(data) - self.sequence_length):
            seq = data[i:i + self.sequence_length]
            sequences.append(seq)
            
            if labels is not None:
                targets.append(labels[i + self.sequence_length])
        
        return np.array(sequences), np.array(targets) if labels is not None else np.array(sequences)
    
    def prepare_by_system(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Prepare data for each system independently.
        
        Args:
            df: Combined workload DataFrame
            
        Returns:
            Dictionary with system_id as key and train/test arrays as values
        """
        logger.info("Preparing sequences by system...")
        
        system_data = {}
        unique_systems = df['system_id'].unique()
        
        for system_id in unique_systems:
            logger.info(f"Processing system: {system_id}")
            
            system_df = df[df['system_id'] == system_id].sort_values('timestamp').reset_index(drop=True)
            
            if len(system_df) < self.sequence_length + 1:
                logger.warning(f"Insufficient data for {system_id} ({len(system_df)} records). Skipping.")
                continue
            
            # Normalize features
            system_normalized = system_df.copy()
            for feature in self.feature_names:
                scaler = MinMaxScaler(feature_range=(0, 1))
                system_normalized[feature] = scaler.fit_transform(system_df[[feature]])
                if system_id not in self.scalers:
                    self.scalers[system_id] = {}
                self.scalers[system_id][feature] = scaler
            
            # Create feature matrix
            features = system_normalized[self.feature_names].values
            
            # Create sequences
            X, y = self.create_sequences(features, features[:, 0])  # Predict CPU
            
            # Train/test split
            split_idx = int(len(X) * (1 - self.test_split))
            
            system_data[system_id] = {
                'X_train': X[:split_idx],
                'X_test': X[split_idx:],
                'y_train': y[:split_idx],
                'y_test': y[split_idx:],
                'sequence_count': len(X),
                'train_sequences': len(X[:split_idx]),
                'test_sequences': len(X[split_idx:])
            }
            
            logger.info(
                f"  System {system_id}: {len(X)} sequences "
                f"({len(X[:split_idx])} train, {len(X[split_idx:])} test)"
            )
        
        return system_data
    
    def prepare_global(self, df: pd.DataFrame) -> Dict:
        """
        Prepare global dataset combining all systems.
        
        Args:
            df: Combined workload DataFrame
            
        Returns:
            Dictionary with global train/test arrays
        """
        logger.info("Preparing global sequences (all systems combined)...")
        
        # Sort by timestamp globally
        df_sorted = df.sort_values('timestamp').reset_index(drop=True)
        
        # Normalize features
        df_normalized = df_sorted.copy()
        for feature in self.feature_names:
            scaler = MinMaxScaler(feature_range=(0, 1))
            df_normalized[feature] = scaler.fit_transform(df_sorted[[feature]])
            self.scalers[f"global_{feature}"] = scaler
        
        # Create feature matrix
        features = df_normalized[self.feature_names].values
        
        # Create sequences
        X, y = self.create_sequences(features, features[:, 0])  # Predict CPU
        
        # Train/test split
        split_idx = int(len(X) * (1 - self.test_split))
        
        result = {
            'X_train': X[:split_idx],
            'X_test': X[split_idx:],
            'y_train': y[:split_idx],
            'y_test': y[split_idx:],
            'sequence_count': len(X),
            'train_sequences': len(X[:split_idx]),
            'test_sequences': len(X[split_idx:])
        }
        
        logger.info(
            f"Global: {len(X)} sequences "
            f"({len(X[:split_idx])} train, {len(X[split_idx:])} test)"
        )
        
        return result
    
    def save_preprocessed_data(self, data: Dict, output_dir: str, mode: str = 'system'):
        """
        Save preprocessed data and scalers.
        
        Args:
            data: Dictionary containing train/test arrays
            output_dir: Directory to save preprocessed data
            mode: 'system' or 'global'
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving preprocessed data to: {output_path}")
        
        if mode == 'system':
            for system_id, system_data in data.items():
                system_dir = output_path / str(system_id)
                system_dir.mkdir(parents=True, exist_ok=True)
                
                np.save(system_dir / 'X_train.npy', system_data['X_train'])
                np.save(system_dir / 'X_test.npy', system_data['X_test'])
                np.save(system_dir / 'y_train.npy', system_data['y_train'])
                np.save(system_dir / 'y_test.npy', system_data['y_test'])
                
                logger.info(f"Saved data for system: {system_id}")
        
        else:  # global mode
            np.save(output_path / 'X_train.npy', data['X_train'])
            np.save(output_path / 'X_test.npy', data['X_test'])
            np.save(output_path / 'y_train.npy', data['y_train'])
            np.save(output_path / 'y_test.npy', data['y_test'])
            
            logger.info("Saved global preprocessed data")
        
        # Save scalers
        scalers_path = output_path / 'scalers.pkl'
        with open(scalers_path, 'wb') as f:
            pickle.dump(self.scalers, f)
        logger.info(f"Saved scalers to: {scalers_path}")
    
    def get_preprocessing_summary(self, original_df: pd.DataFrame, mode: str = 'system') -> str:
        """Generate summary of preprocessing results."""
        summary = f"""
Preprocessing Summary
{'='*80}
Configuration:
  - Sequence length: {self.sequence_length} timesteps
  - Test split: {self.test_split * 100:.0f}%
  - Features: {', '.join(self.feature_names)}

Input Data:
  - Total records: {len(original_df)}
  - Unique systems: {original_df['system_id'].nunique()}
  - Date range: {original_df['timestamp'].min():.0f} to {original_df['timestamp'].max():.0f}

Features scaled to [0, 1] using MinMaxScaler for stable LSTM training.
Sequences created with {self.sequence_length} timesteps for temporal pattern capture.
Each sample predicts CPU usage at next timestep.
{'='*80}
    """
        return summary


def main():
    """Main execution block."""
    
    INPUT_DATA = r"D:\Research\Operation\green-devops-operation-component\data\processed\workload_data.csv"
    OUTPUT_DIR_SYSTEM = r"D:\Research\Operation\green-devops-operation-component\data\preprocessed\system"
    OUTPUT_DIR_GLOBAL = r"D:\Research\Operation\green-devops-operation-component\data\preprocessed\global"
    
    try:
        # Initialize preprocessor
        logger.info("Initializing LSTM preprocessor...")
        preprocessor = LSTMPreprocessor(sequence_length=12, test_split=0.2)
        
        # Load data
        df = preprocessor.load_data(INPUT_DATA)
        
        # Print summary before preprocessing
        print(preprocessor.get_preprocessing_summary(df, mode='system'))
        
        # Prepare by system
        logger.info("\n" + "="*80)
        logger.info("PREPARING DATA BY SYSTEM")
        logger.info("="*80)
        system_data = preprocessor.prepare_by_system(df)
        preprocessor.save_preprocessed_data(system_data, OUTPUT_DIR_SYSTEM, mode='system')
        
        # Prepare global
        logger.info("\n" + "="*80)
        logger.info("PREPARING GLOBAL DATA")
        logger.info("="*80)
        global_data = preprocessor.prepare_global(df)
        preprocessor.save_preprocessed_data(global_data, OUTPUT_DIR_GLOBAL, mode='global')
        
        logger.info("\n" + "="*80)
        logger.info("PREPROCESSING COMPLETE")
        logger.info("="*80)
        
        print(f"\nSystem-level data saved to: {OUTPUT_DIR_SYSTEM}")
        print(f"Global data saved to: {OUTPUT_DIR_GLOBAL}")
        print(f"Scalers saved with both datasets")
        print("\nReady for LSTM model training!")
        
        return preprocessor, system_data, global_data
        
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        raise


if __name__ == "__main__":
    preprocessor, system_data, global_data = main()
