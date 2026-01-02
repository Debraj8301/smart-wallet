from pdf_processor import extract_statement_data
import json
from tabulate import tabulate

def test_extractions():
    files = [
        "../statements/GPay_Transaction_Statement.pdf",
        "../statements/PhonePe_Transaction_Statement.pdf",
        "../statements/SBI Card Statement_5423_16-12-2025.PDF",
        "../statements/bank_statement_latest.pdf"
    ]
    
    for f in files:
        print(f"\nTesting extraction for: {f}")
        data = extract_statement_data(f)
        print(f"Extracted {len(data)} transactions.")
        if data:
            print(tabulate(data, headers="keys", tablefmt="grid"))
        else:
            print("No transactions extracted.")

if __name__ == "__main__":
    test_extractions()
