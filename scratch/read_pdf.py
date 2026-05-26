import os
# pyrefly: ignore [missing-import]
from pypdf import PdfReader

pdf_path = os.path.join("patient_records", "medical-bill_compress.pdf")
print("Reading", pdf_path)
reader = PdfReader(pdf_path)
print("Pages:", len(reader.pages))
for i, page in enumerate(reader.pages):
    print(f"--- Page {i+1} ---")
    print(page.extract_text()[:2000]) # Print first 2000 chars of each page
