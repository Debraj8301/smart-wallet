import pdfplumber
import re
from datetime import datetime

def parse_amount(amount_str):
    if not amount_str:
        return 0.0
    # Remove currency symbols and commas
    cleaned = re.sub(r'[^\d.-]', '', str(amount_str))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def extract_gpay_statement(pdf):
    transactions = []
    # GPay statements often don't extract well as standard tables.
    # We might need to look for specific patterns or text blocks.
    # Based on analysis: "Date&time Transactiondetails Amount"
    # But pdfplumber table extraction showed: ['Transactionstatementperiod Sent Received...']
    # which implies the main list might not be detected as a table easily or is on subsequent pages.
    
    # Let's try to iterate through pages and look for transaction blocks
    # Pattern seen: "01Nov,2025 Paidto..."
    
    date_pattern = r'(\d{2}[A-Za-z]{3},\d{4})'
    
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
            
        lines = text.split('\n')
        current_date = None
        
        for i, line in enumerate(lines):
            # Very basic heuristic for GPay based on the text dump
            # Real implementation needs to be robust against layout variations
            match = re.search(date_pattern, line)
            if match:
                current_date = match.group(1)
                # Try to extract amount and details from this or next lines
                # This is tricky without a structured table.
                # For this MVP, we will try to find lines with '₹'
                
            if '₹' in line and current_date:
                # Attempt to parse line like: "PaidtoBlinkit ₹425"
                parts = line.split('₹')
                if len(parts) >= 2:
                    details = parts[0].strip()
                    details = details.replace(current_date, "").strip()
                    details = re.sub(date_pattern, "", details).strip()
                    amount_str = parts[1].split()[0] # Take first part after symbol
                    
                    t_type = "Credit" if "Received" in details else "Debit"
                    
                    transactions.append({
                        "date": current_date,
                        "transaction_details": details,
                        "amount": parse_amount(amount_str),
                        "type": t_type
                    })
    return transactions

def extract_phonepe_statement(pdf):
    transactions = []
    
    # Heuristic text-based extraction since table extraction is failing to map correctly
    # Pattern: "Date Transaction Details Type Amount" header
    # Rows: "Nov 25, 2025 Received from... Credit INR 3000.00"
    
    date_pattern = r'([A-Za-z]{3}\s\d{1,2},\s\d{4})' # e.g. Nov 25, 2025
    
    for page in pdf.pages:
        text = page.extract_text()
        if not text: continue
        
        # Split text into chunks or lines. 
        # PhonePe PDF text often comes out line by line.
        lines = text.split('\n')
        
        current_txn = {}
        
        for i, line in enumerate(lines):
            # Check for start of a transaction (Date)
            date_match = re.search(date_pattern, line)
            
            if date_match and ("Credit" in line or "Debit" in line):
                # Single line transaction?
                # "Nov 25, 2025 Paid to ... Debit INR 500.00"
                parts = line.split()
                # Last part is amount? "500.00"
                # Type is "Debit" or "Credit"
                
                try:
                    amount_str = parts[-1]
                    # Check if amount is valid number
                    parse_amount(amount_str) 
                    
                    t_type = "Credit" if "Credit" in line else "Debit"
                    
                    # Details are between Date and Type
                    # Date is usually first 3 parts: "Nov 25, 2025"
                    date_str = date_match.group(1)
                    
                    # This is rough, assumes "Credit INR" or "Debit INR" structure
                    split_keyword = "Credit" if "Credit" in line else "Debit"
                    details_part = line.split(split_keyword)[0]
                    details = details_part.replace(date_str, "").strip()
                    
                    transactions.append({
                        "date": date_str,
                        "transaction_details": details,
                        "amount": parse_amount(amount_str),
                        "type": t_type
                    })
                    continue
                except:
                    pass
            
            # Multi-line handling logic would be needed if the above simple logic fails
            # But looking at the debug text dump earlier:
            # "Nov 25, 2025 Received from ... Credit INR"
            # "08:45 PM Transaction ID ... 30000.00" -> Amount is on next line!
            
            if date_match and not ("Credit" in line or "Debit" in line):
                 # Might be just date and start of details
                 pass

            # Alternative Strategy: Look for blocks starting with Date
            if date_match:
                # This line starts a transaction block
                # We need to look ahead for Amount and Type
                # The text dump showed:
                # Line 1: Nov 25, 2025 Received from SUPARNA... Credit INR
                # Line 2: 08:45 PM Transaction ID ... 30000.00
                
                date_str = date_match.group(1)
                
                # Check current line for Type (default to Debit to avoid Unknown)
                t_type = "Debit"
                if "Credit" in line or "Received" in line: 
                    t_type = "Credit"
                elif "Debit" in line or "Paid" in line: 
                    t_type = "Debit"
                
                details = line.replace(date_str, "").replace("Credit", "").replace("Debit", "").replace("INR", "").strip()
                details = re.sub(r"^[-–—]+\s*", "", details)
                
                # Look at next few lines for Amount
                amount = 0.0
                if i + 1 < len(lines):
                    # Check next 3 lines just in case
                    for offset in range(1, 4):
                         if i + offset >= len(lines): break
                         next_line = lines[i+offset]
                         # Heuristic: Amount usually has a decimal point and is at the end or standalone
                         # Example: "Transaction ID ... 30000.00"
                         # Or just "30000.00"
                         
                         parts = next_line.split()
                         if not parts: continue
                         
                         possible_amt_str = parts[-1]
                         # Remove commas
                         possible_amt_str = possible_amt_str.replace(',', '')
                         
                         # Check if it looks like a number
                         if re.match(r'^\d+(\.\d+)?$', possible_amt_str):
                             amount = parse_amount(possible_amt_str)
                             break
                
                if amount > 0:
                    if t_type == "Debit":
                        if re.search(r"Received", details, re.IGNORECASE):
                            t_type = "Credit"
                    transactions.append({
                        "date": date_str,
                        "transaction_details": details,
                        "amount": amount,
                        "type": t_type
                    })

    return transactions

def extract_sbi_statement(pdf):
    transactions = []
    # Table headers: ['Date', 'Transaction Details...', 'Amount ( ` )']
    # The amount column has 'C' or 'D' suffix often
    
    def is_sbi_transactions_table(table):
        if not table or len(table) < 2:
            return False
        header = table[0]
        header_texts = [str(c) if c else '' for c in header]
        has_date = any('Date' in h for h in header_texts)
        has_amount_header = any('Amount' in h for h in header_texts)
        if not (has_date and has_amount_header):
            return False
        amount_pattern = re.compile(r'[\d,]+(?:\.\d+)?\s*[CD]')
        for row in table[1:]:
            if len(row) >= 3 and row[2] and amount_pattern.search(str(row[2])):
                return True
        return False
    
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table: 
                continue
            if not is_sbi_transactions_table(table):
                continue
            
            # Check headers
            start_idx = 0
            if table[0] and 'Date' in str(table[0][0]):
                start_idx = 1
            
            # Note: SBI sample analysis showed a messy table where columns might be merged
            # Row 0: ['Date', 'Transaction Details...', 'Amount']
            # Row 1: ['16 Nov 25\n26 Nov 25...', 'CARD CASHBACK...', '1,014.00 C\n...']
            # This indicates pdfplumber merged multiple rows into one cell due to lack of grid lines
            
                for row in table[start_idx:]:
                    # If cells contain newlines, we might need to split them and align
                    if len(row) >= 3 and row[0] and row[1] and row[2]:
                        dates = str(row[0]).split('\n')
                        details = str(row[1]).split('\n')
                        amounts = str(row[2]).split('\n')
                        
                        # This is a heuristic assuming equal number of lines per cell, which is risky
                        # But often true for these specific PDF structures
                        count = min(len(dates), len(details), len(amounts))
                        
                        for i in range(count):
                            amt_raw = amounts[i]
                            t_type = "Credit" if 'C' in amt_raw else "Debit" if 'D' in amt_raw else "Debit"
                            
                            amt_val = parse_amount(amt_raw)
                            if amt_val > 0:
                                transactions.append({
                                    "date": dates[i],
                                    "transaction_details": details[i],
                                    "amount": amt_val,
                                    "type": t_type
                                })
    return transactions

def extract_axis_statement(pdf):
    transactions = []
    # Table headers: ['Tran Date', 'Chq No', 'Particulars', 'Debit', 'Credit', 'Balance', 'Init. Br']
    
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table: continue
            
            start_idx = 0
            if table[0] and 'Tran Date' in str(table[0][0]):
                start_idx = 1
                
            for row in table[start_idx:]:
                if len(row) < 5: continue
                
                date_str = row[0]
                if not date_str: continue # Skip empty rows (like opening balance sometimes)
                
                details = row[2].replace('\n', ' ') if row[2] else ""
                debit = row[3]
                credit = row[4]
                
                amount = 0.0
                t_type = "Debit"
                
                if debit and debit.strip():
                    amount = parse_amount(debit)
                    t_type = "Debit"
                elif credit and credit.strip():
                    amount = parse_amount(credit)
                    t_type = "Credit"
                
                if amount > 0:
                    transactions.append({
                        "date": date_str,
                        "transaction_details": details,
                        "amount": amount,
                        "type": t_type
                    })
    return transactions

def extract_generic_statement(pdf):
    transactions = []
    print("Attempting generic extraction...")
    
    # Generic regex for Date (DD-MM-YYYY, DD/MM/YYYY, DD MMM YYYY, etc.)
    # 25 Nov 2025, 25-11-2025, 2025-11-25
    date_pattern = re.compile(r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b')
    
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
            
        lines = text.split('\n')
        for line in lines:
            # Look for a date
            date_match = date_pattern.search(line)
            if date_match:
                # Look for an amount
                # Heuristic: Amount is usually at the end, contains digits and maybe decimal
                # Exclude years (2025) if they match number pattern
                parts = line.split()
                amount = 0.0
                t_type = "Debit" # Default
                
                # Check keywords for type
                if "Cr" in line or "Credit" in line or "Received" in line:
                    t_type = "Credit"
                
                # Try to find amount from right to left
                for part in reversed(parts):
                    # Clean part
                    clean_part = re.sub(r'[^\d.]', '', part)
                    if not clean_part:
                        continue
                    # Avoid date parts like '2025' or small integers unless they look like currency
                    if re.match(r'^\d+(\.\d{1,2})?$', clean_part):
                        try:
                            val = float(clean_part)
                            # Simple heuristic: filter out years or days if they are standalone
                            if val > 1900 and val < 2100 and val.is_integer():
                                # Likely a year, skip unless it has decimal
                                if '.' in part:
                                     amount = val
                                     break
                            else:
                                amount = val
                                break
                        except:
                            pass
                
                if amount > 0:
                    date_str = date_match.group(0)
                    # Details: Everything else
                    details = line.replace(date_str, "").strip()
                    # Remove amount from details if possible (rough)
                    # For now just keep it simple
                    
                    transactions.append({
                        "date": date_str,
                        "transaction_details": details,
                        "amount": amount,
                        "type": t_type
                    })
    
    return transactions

def extract_statement_data(file_path, original_filename=None):
    transactions = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            # Detect statement type based on content of first page
            first_page_text = ""
            try:
                if pdf.pages:
                    first_page_text = pdf.pages[0].extract_text() or ""
            except Exception as e:
                print(f"Warning: Failed to extract text from first page: {e}")

            # Combine file_path and original_filename for checking
            name_check = file_path
            if original_filename:
                name_check += " " + original_filename
            
            print(f"Analyzing PDF: {original_filename}")
            
            if "PhonePe" in first_page_text or "PhonePe" in name_check:
                print("Detected PhonePe Statement")
                transactions = extract_phonepe_statement(pdf)
            elif "SBI Card" in first_page_text or "SBI Card" in name_check: 
                print("Detected SBI Card Statement")
                transactions = extract_sbi_statement(pdf)
            elif "Axis Account" in first_page_text or "AXIS BANK" in first_page_text.upper():
                print("Detected Axis Bank Statement")
                transactions = extract_axis_statement(pdf)
            elif "gpay" in name_check.lower() or "google pay" in first_page_text.lower():
                print("Detected GPay Statement")
                transactions = extract_gpay_statement(pdf)
            else:
                print("Unknown statement type. Attempting generic extraction...")
                transactions = extract_generic_statement(pdf)
                
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        
    return transactions
