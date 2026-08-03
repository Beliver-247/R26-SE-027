from setuptools import setup, find_packages

setup(
    name="green-devops-operation-component",
    version="1.0.0",
    description="Carbon-aware autoscaling and job optimization for Kubernetes",
    author="Research Team",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "fastapi>=0.95.0",
        "uvicorn>=0.20.0",
        "pydantic>=1.10.0",
        "prometheus-client>=0.16.0",
        "kubernetes>=25.0.0",
        "pandas>=1.5.0",
        "numpy>=1.23.0",
        "scikit-learn>=1.2.0",
        "tensorflow>=2.12.0",
        "PyYAML>=6.0",
        "python-dotenv>=0.21.0",
        "APScheduler>=3.10.0",
        "requests>=2.28.0",
        "joblib>=1.2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.2.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "jupyter>=1.0.0",
            "ipython>=8.10.0",
        ],
    },
)
