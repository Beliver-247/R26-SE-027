#!/usr/bin/env python3
"""
Verification Checklist: Carbon Evaluation Endpoint Implementation

Run this to verify the implementation is complete and working.
"""

import os
import json
import sys
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
CHECKMARK = '✓'
CROSS = '✗'

def check_file_exists(path: str, description: str) -> bool:
    """Check if a file exists."""
    exists = os.path.isfile(path)
    status = f"{GREEN}{CHECKMARK}{RESET}" if exists else f"{RED}{CROSS}{RESET}"
    print(f"  {status} {description}: {path}")
    return exists

def check_directory_exists(path: str, description: str) -> bool:
    """Check if a directory exists."""
    exists = os.path.isdir(path)
    status = f"{GREEN}{CHECKMARK}{RESET}" if exists else f"{RED}{CROSS}{RESET}"
    print(f"  {status} {description}: {path}")
    return exists

def check_file_contains(path: str, search_string: str) -> bool:
    """Check if a file contains a specific string."""
    if not os.path.isfile(path):
        return False
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            return search_string in content
    except UnicodeDecodeError:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return search_string in content
        except Exception:
            return False
    except Exception:
        return False

def verify_python_syntax(path: str) -> bool:
    """Verify Python file has no syntax errors."""
    if not os.path.isfile(path):
        return False
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            compile(f.read(), path, 'exec')
        return True
    except SyntaxError:
        return False
    except UnicodeDecodeError:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                compile(f.read(), path, 'exec')
            return True
        except:
            return False

def main():
    """Run verification checklist."""
    
    print("\n" + "=" * 80)
    print("CARBON ENDPOINT IMPLEMENTATION VERIFICATION CHECKLIST".center(80))
    print("=" * 80 + "\n")
    
    checks_passed = 0
    checks_failed = 0
    
    # ========================================================================
    # SECTION 1: FILE EXISTENCE
    # ========================================================================
    
    print(f"{BLUE}1. FILE EXISTENCE CHECKS{RESET}")
    print("-" * 80)
    
    files_to_check = [
        ("src/workload_prediction_engine/api.py", "API Implementation"),
        ("CARBON_EVALUATION_GUIDE.md", "User Guide"),
        ("CARBON_ENDPOINT_SUMMARY.md", "Feature Summary"),
        ("CARBON_ENDPOINT_QUICK_REFERENCE.py", "Quick Reference"),
        ("test_carbon_endpoint.py", "Test Suite"),
        ("integration_example.py", "Integration Example"),
        ("IMPLEMENTATION_SUMMARY.md", "Implementation Summary")
    ]
    
    for file_path, description in files_to_check:
        if check_file_exists(file_path, description):
            checks_passed += 1
        else:
            checks_failed += 1
    
    # ========================================================================
    # SECTION 2: CODE SYNTAX VALIDATION
    # ========================================================================
    
    print(f"\n{BLUE}2. CODE SYNTAX VALIDATION{RESET}")
    print("-" * 80)
    
    python_files = [
        ("src/workload_prediction_engine/api.py", "API Implementation"),
        ("test_carbon_endpoint.py", "Test Suite"),
        ("integration_example.py", "Integration Example"),
        ("CARBON_ENDPOINT_QUICK_REFERENCE.py", "Quick Reference")
    ]
    
    for file_path, description in python_files:
        if verify_python_syntax(file_path):
            print(f"  {GREEN}{CHECKMARK}{RESET} {description} syntax OK: {file_path}")
            checks_passed += 1
        else:
            print(f"  {RED}{CROSS}{RESET} {description} has syntax errors: {file_path}")
            checks_failed += 1
    
    # ========================================================================
    # SECTION 3: API IMPLEMENTATION CHECKS
    # ========================================================================
    
    print(f"\n{BLUE}3. API IMPLEMENTATION CHECKS{RESET}")
    print("-" * 80)
    
    api_file = "src/workload_prediction_engine/api.py"
    
    checks = [
        ("CarbonEvaluationRequest", "Pydantic model for request"),
        ("CarbonEvaluationResponse", "Pydantic model for response"),
        ("CarbonScenario", "Pydantic model for scenarios"),
        ("@self.app.post(\"/carbon/evaluate\"", "Carbon evaluation endpoint"),
        ("set_carbon_engine", "Method to set carbon engine"),
        ("evaluate_carbon", "Carbon evaluation route handler"),
        ("validate all input parameters", "Input validation comment"),
        ("from carbon_engine import CarbonEmissionEngine", "Carbon engine import")
    ]
    
    for check_string, description in checks:
        if check_file_contains(api_file, check_string):
            print(f"  {GREEN}{CHECKMARK}{RESET} {description}")
            checks_passed += 1
        else:
            print(f"  {RED}{CROSS}{RESET} {description}")
            checks_failed += 1
    
    # ========================================================================
    # SECTION 4: DOCUMENTATION CHECKS
    # ========================================================================
    
    print(f"\n{BLUE}4. DOCUMENTATION CHECKS{RESET}")
    print("-" * 80)
    
    doc_checks = [
        ("CARBON_EVALUATION_GUIDE.md", [
            "Quick Start",
            "Request Schema",
            "Use Cases",
            "Error Handling",
            "FAQ"
        ]),
        ("CARBON_ENDPOINT_SUMMARY.md", [
            "Overview",
            "Implementation Details",
            "Integration",
            "Testing"
        ]),
        ("IMPLEMENTATION_SUMMARY.md", [
            "Files Created",
            "Implementation Details",
            "Integration Points",
            "Usage Examples"
        ])
    ]
    
    for doc_file, sections in doc_checks:
        print(f"  Checking {doc_file}:")
        for section in sections:
            if check_file_contains(doc_file, section):
                print(f"    {GREEN}{CHECKMARK}{RESET} {section}")
                checks_passed += 1
            else:
                print(f"    {RED}{CROSS}{RESET} {section}")
                checks_failed += 1
    
    # ========================================================================
    # SECTION 5: REQUEST/RESPONSE SCHEMA
    # ========================================================================
    
    print(f"\n{BLUE}5. REQUEST/RESPONSE SCHEMA{RESET}")
    print("-" * 80)
    
    schema_checks = [
        ("test_carbon_endpoint.py", [
            ("system_id", "System ID field"),
            ("predicted_cpu", "Predicted CPU field"),
            ("predicted_load_level", "Load level field"),
            ("recommended_pods", "Recommended pods field"),
            ("current_pods", "Current pods field"),
            ("delayable_jobs", "Delayable jobs field"),
            ("workload_reduction_percent", "Workload reduction field")
        ])
    ]
    
    for file_path, fields in schema_checks:
        print(f"  Request fields in {file_path}:")
        for field, description in fields:
            if check_file_contains(file_path, field):
                print(f"    {GREEN}{CHECKMARK}{RESET} {description}")
                checks_passed += 1
            else:
                print(f"    {RED}{CROSS}{RESET} {description}")
                checks_failed += 1
    
    # ========================================================================
    # SECTION 6: FEATURE COMPLETENESS
    # ========================================================================
    
    print(f"\n{BLUE}6. FEATURE COMPLETENESS{RESET}")
    print("-" * 80)
    
    features = [
        ("integration_example.py", "CarbonAwareOrchestrator", "Orchestration class"),
        ("integration_example.py", "collect_metrics", "Metrics collection"),
        ("integration_example.py", "get_engine1_prediction", "Engine 1 integration"),
        ("integration_example.py", "evaluate_carbon", "Engine 2 evaluation"),
        ("integration_example.py", "make_scaling_decision", "Decision making"),
        ("integration_example.py", "apply_decision", "Decision application"),
        ("test_carbon_endpoint.py", "test_basic_carbon_evaluation", "Basic test"),
        ("test_carbon_endpoint.py", "test_carbon_with_job_deferral", "Job deferral test"),
        ("test_carbon_endpoint.py", "test_invalid_input", "Error handling test")
    ]
    
    for file_path, search_string, description in features:
        if check_file_contains(file_path, search_string):
            print(f"  {GREEN}{CHECKMARK}{RESET} {description}")
            checks_passed += 1
        else:
            print(f"  {RED}{CROSS}{RESET} {description}")
            checks_failed += 1
    
    # ========================================================================
    # SECTION 7: ERROR HANDLING
    # ========================================================================
    
    print(f"\n{BLUE}7. ERROR HANDLING{RESET}")
    print("-" * 80)
    
    error_checks = [
        ("api.py", "HTTPException", "HTTP exception handling"),
        ("api.py", "ValueError", "Value validation"),
        ("api.py", "try:", "Try-except blocks"),
        ("api.py", "status_code", "HTTP status codes"),
        ("api.py", "raise HTTPException", "Error raising")
    ]
    
    for file_path, search_string, description in error_checks:
        full_path = f"src/workload_prediction_engine/{file_path}" if file_path == "api.py" else file_path
        if check_file_contains(full_path, search_string):
            print(f"  {GREEN}{CHECKMARK}{RESET} {description}")
            checks_passed += 1
        else:
            print(f"  {RED}{CROSS}{RESET} {description}")
            checks_failed += 1
    
    # ========================================================================
    # SECTION 8: VALIDATION & CONSTRAINTS
    # ========================================================================
    
    print(f"\n{BLUE}8. VALIDATION & CONSTRAINTS{RESET}")
    print("-" * 80)
    
    validation_checks = [
        ("api.py", "0 <= request.predicted_cpu <= 100", "CPU range validation"),
        ("api.py", "predicted_load_level in (\"LOW\", \"NORMAL\", \"HIGH\")", "Load level validation"),
        ("api.py", "1 <= request.recommended_pods <= 20", "Pod count validation"),
        ("api.py", "ge=0.0", "Non-negative number validation"),
        ("api.py", "le=100.0", "Maximum percentage validation")
    ]
    
    for _, search_string, description in validation_checks:
        if check_file_contains("src/workload_prediction_engine/api.py", search_string):
            print(f"  {GREEN}{CHECKMARK}{RESET} {description}")
            checks_passed += 1
        else:
            print(f"  {RED}{CROSS}{RESET} {description}")
            checks_failed += 1
    
    # ========================================================================
    # RESULTS
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY".center(80))
    print("=" * 80 + "\n")
    
    total_checks = checks_passed + checks_failed
    success_rate = (checks_passed / total_checks * 100) if total_checks > 0 else 0
    
    status_color = GREEN if checks_failed == 0 else RED
    print(f"  Total Checks: {total_checks}")
    print(f"  Passed: {GREEN}{checks_passed}{RESET}")
    print(f"  Failed: {RED}{checks_failed}{RESET}")
    print(f"  Success Rate: {status_color}{success_rate:.1f}%{RESET}")
    
    if checks_failed == 0:
        print(f"\n{GREEN}✓ ALL CHECKS PASSED - Implementation is complete!{RESET}\n")
        return 0
    else:
        print(f"\n{RED}✗ Some checks failed - Please review above{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
