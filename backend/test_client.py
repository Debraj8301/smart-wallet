import requests
import os

# Create a dummy PDF file for testing
with open("test_doc.pdf", "wb") as f:
    f.write(b"%PDF-1.4 header dummy content")

url = "http://127.0.0.1:8000/upload-statement/"
files = {'file': ('test_doc.pdf', open('test_doc.pdf', 'rb'), 'application/pdf')}
data = {'statement_type': 'UPI'}

try:
    print(f"Sending POST request to {url} with Multipart Form-Data...")
    response = requests.post(url, files=files, data=data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.json()}")
    
    if response.status_code == 202:
        print("SUCCESS: File uploaded successfully for background processing.")
    else:
        print("FAILURE: Upload failed.")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Cleanup
    if os.path.exists("test_doc.pdf"):
        os.remove("test_doc.pdf")
