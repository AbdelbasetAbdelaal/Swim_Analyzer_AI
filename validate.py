import argparse
import sys
from validation.reference_loader import ReferenceLoader
from validation.metrics_validator import MetricsValidator
from validation.validation_report import ValidationReportGenerator

def main():
    parser = argparse.ArgumentParser(description="Run biomechanics validation.")
    parser.add_argument("--labels", type=str, required=True, help="Path to ground truth labels JSON")
    parser.add_argument("--predictions", type=str, required=True, help="Path to predictions JSON")
    args = parser.parse_args()

    try:
        ground_truth = ReferenceLoader.load(args.labels)
        prediction = ReferenceLoader.load(args.predictions)
    except Exception as e:
        print(f"Error loading files: {e}")
        sys.exit(1)

    validator = MetricsValidator(phase_tolerance_frames=5)
    result = validator.validate(ground_truth, prediction)

    text_report = ValidationReportGenerator.generate_text_report(result)
    json_report = ValidationReportGenerator.generate_json_report(result)

    with open("validation_report.txt", "w", encoding="utf-8") as f:
        f.write(text_report)

    with open("validation_report.json", "w", encoding="utf-8") as f:
        f.write(json_report)
        
    print("Validation reports generated successfully (validation_report.txt, validation_report.json).")

if __name__ == "__main__":
    main()
