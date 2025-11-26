from fastapi import APIRouter, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
from pypdf import PdfReader
import asyncio
import io
import re
from typing import List

pdf_analyzer_router = APIRouter(tags=["pdf_analyzer_router"])

client = OpenAI()

# PDF 텍스트 추출
def extract_text_from_pdf_clean(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        texts = []
        for page in reader.pages:
            t = page.extract_text() or ""
            t = re.sub(r'\s+', ' ', t)                # 공백 정리
            t = re.sub(r'\d+\s*$', '', t)            # 페이지 번호 제거
            if t.strip():
                texts.append(t.strip())
        return "\n".join(texts)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF parsing error: {str(e)}")

# 텍스트 청킹
def chunk_text(text: str, chunk_size=3500, overlap=300) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, cur = [], ""
    for p in paragraphs:
        if len(cur) + len(p) <= chunk_size:
            cur += " " + p
        else:
            chunks.append(cur.strip())
            cur = p
    if cur:
        chunks.append(cur.strip())
    return chunks

# GPT 호출 래퍼
async def ask_gpt(prompt: str, max_tokens=500):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda:
        client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0
        ).choices[0].message.content
    )

# 문서 요약 에이전트 (섹션 요약 후 전체 요약)
async def summarize_document(chunks: List[str]) -> str:
    partial_summaries = []

    for idx, chunk in enumerate(chunks):
        prompt = f"""
다음은 문서의 일부이다. 이 문단을 핵심 내용만 유지하며 간결하게 요약해라.

문단({idx+1}):
{chunk}
"""
        summary = await ask_gpt(prompt, max_tokens=400)
        partial_summaries.append(summary)

    merged = "\n".join(partial_summaries)

    # 전체 요약
    final_prompt = f"""
다음은 여러 요약문을 결합한 것이다. 이 내용을 다시 한 번 전체 핵심만 유지하며 통합 요약해라.

내용:
{merged}

출력 형식:
- 전체 요약 1개 문단
"""
    final_summary = await ask_gpt(final_prompt, max_tokens=500)
    return final_summary.strip()

# QA 에이전트
async def qa_on_document(summary: str, question: str) -> str:
    prompt = f"""
다음은 문서 요약이다. 이 요약 내의 정보만 사용하여 질문에 답해라.

요약:
{summary}

질문:
{question}

규칙:
- 추론하지 말고 요약 내에서만 답을 찾아라.
- 없으면 "문서에 해당 정보 없음"이라고 답해라.
"""
    return (await ask_gpt(prompt, max_tokens=300)).strip()

# 감성 분석 + 키포인트 에이전트
async def analyze_opinions(summary: str) -> dict:
    prompt = f"""
다음 문서 요약에 대해 감성 분석과 핵심 포인트 추출을 수행해라.

요약:
{summary}

출력 형식(JSON):
{{
    "sentiment": "positive | negative | neutral",
    "key_points": ["핵심 문장1", "핵심 문장2", ... 5개]
}}
"""
    raw = await ask_gpt(prompt, max_tokens=300)

    import json
    try:
        return json.loads(raw)
    except:
        return {"sentiment": "unknown", "key_points": []}

@documents_openai_router.post("/analyze")
async def analyze_document(file: UploadFile, question: str = Form(...)):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(400, "Empty file upload")

        text = extract_text_from_pdf_clean(content)
        if not text:
            raise HTTPException(400, "No text extracted")

        chunks = chunk_text(text)
        if not chunks:
            raise HTTPException(500, "Chunking failed")

        # 1. 요약
        summary = await summarize_document(chunks)

        # 2. QA
        answer = await qa_on_document(summary, question)

        # 3. 감성 분석 + 키포인트
        analysis = await analyze_opinions(summary)

        return JSONResponse({
            "parsed_text": text,
            "summary": summary,
            "answer": answer,
            "analysis": analysis
        })

    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {str(e)}")
