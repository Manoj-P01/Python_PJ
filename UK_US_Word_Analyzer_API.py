from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.background import BackgroundTasks
from typing import Dict, List, Tuple, Any
import docx2txt
from collections import defaultdict
import os
import tempfile
import re
app = FastAPI(title="UK/US Word Analyzer API")

def load_dictionary(dict_path: str) -> set:
    """Load dictionary words from a file"""
    with open(dict_path, 'r', encoding='utf-8') as f:
        return set(word.strip().lower() for word in f.readlines() if word.strip())
async def extract_text_from_docx(file_content: bytes) -> str:
    """
    Extract text content from DOCX file bytes
    
    Args:
        file_content: DOCX file content as bytes
        
    Returns:
        Extracted text as string
        
    Raises:
        HTTPException: If file processing fails
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
        temp_file.write(file_content)
        temp_path = temp_file.name
    
    try:
        return docx2txt.process(temp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX processing failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

async def analyze_docx(file_content: bytes, us_words: set, uk_words: set) -> Dict[str, Any]:
    """
    Analyze DOCX content for UK/US word matches
    """
    
    try:
        # Process DOCX file
        text = await extract_text_from_docx(file_content)
        words = text.lower().split()
        
        # Initialize results
        results = {
            'us': {'total': 0, 'words': defaultdict(int)},
            'uk': {'total': 0, 'words': defaultdict(int)},
            'total_words_in_document': len(words)
        }
        
        # Check each word against dictionaries
        for word in words:
            clean_word = word.strip(".,!?()\"'")
            if clean_word:
                if clean_word in us_words:
                    results['us']['words'][clean_word] += 1
                    results['us']['total'] += 1
                if clean_word in uk_words:
                    results['uk']['words'][clean_word] += 1
                    results['uk']['total'] += 1
        
        # Convert defaultdict to regular dict
        results['us']['words'] = dict(results['us']['words'])
        results['uk']['words'] = dict(results['uk']['words'])
        
        return results
    
    except HTTPException:
        raise  # Re-raise existing HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

def generate_report_content(results: dict) -> str:
    """Generate report content as string"""
    report_content = "=== DOCUMENT ANALYSIS REPORT ===\n"
    report_content += f"Total Words: {results['total_words_in_document']}\n\n"
    
    report_content += "US Words \n"
    report_content += f"Total Words : {results['us']['total']}\n"
    for word, count in results['us']['words'].items():
        report_content += f"{word}: {count}\n"
    
    report_content += "\nUK Words \n"
    report_content += f"Total Words : {results['uk']['total']}\n"
    for word, count in results['uk']['words'].items():
        report_content += f"{word}: {count}\n"
    
    return report_content

def cleanup_tempfile(path: str):
    """Clean up temporary file"""
    if os.path.exists(path):
        os.unlink(path)

@app.post("/analyze", response_model=Dict[str, Any])
async def analyze_document(
    file: UploadFile = File(...) 
):
    """
    Analyze a DOCX file for UK/US word usage
    """
    try:
        
        # Check file type
        if not file.filename.endswith('.docx'):
            raise HTTPException(status_code=400, detail="Only DOCX files are supported")
        us_dict_path = os.getenv("US_DICT_PATH", "us_dict.txt")
        uk_dict_path = os.getenv("UK_DICT_PATH", "uk_dict.txt")
        # Load dictionaries
        if not os.path.exists(us_dict_path):
            raise HTTPException(status_code=404, detail="US dictionary file not found")
        if not os.path.exists(uk_dict_path):
            raise HTTPException(status_code=404, detail="UK dictionary file not found")
            
        us_words = load_dictionary(us_dict_path)
        uk_words = load_dictionary(uk_dict_path)
        
        # Analyze document
        file_content = await file.read()
        results = await analyze_docx(file_content, us_words, uk_words)
        
        return JSONResponse(content=results)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-and-download")
async def analyze_and_download(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Analyze a DOCX file and return a text report download
    """
    try:
        # Check file type
        if not file.filename.endswith('.docx'):
            raise HTTPException(status_code=400, detail="Only DOCX files are supported")
        
        # Load dictionaries
        us_dict_path = os.getenv("US_DICT_PATH", "us_dict.txt")
        uk_dict_path = os.getenv("UK_DICT_PATH", "uk_dict.txt")
        if not os.path.exists(us_dict_path):
            raise HTTPException(status_code=404, detail="US dictionary file not found")
        if not os.path.exists(uk_dict_path):
            raise HTTPException(status_code=404, detail="UK dictionary file not found")
            
        us_words = load_dictionary(us_dict_path)
        uk_words = load_dictionary(uk_dict_path)
        
        # Analyze document
        file_content = await file.read()
        results = await analyze_docx(file_content, us_words, uk_words)
        
        # Generate report content
        report_content = generate_report_content(results)
        
        # Create temporary report file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp:
            tmp.write(report_content)
            tmp_path = tmp.name
        
        # Schedule cleanup after response is sent
        background_tasks.add_task(cleanup_tempfile, tmp_path)
        
        return FileResponse(
            tmp_path,
            media_type="text/plain",
            filename="word_analysis_report.txt",
            headers={"Content-Disposition": "attachment; filename=word_analysis_report.txt"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
