from urllib.parse import urlparse

import boto3
from botocore.exceptions import NoCredentialsError
from fastapi import APIRouter, Form, HTTPException
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from openai import OpenAI
from pypdf import PdfReader
import asyncio
import io
import re
from typing import List

from account.adapter.input.web.session_helper import get_current_user

pdf_analyzer_router = APIRouter(tags=["pdf-analyzer"])

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
        # 1. 섹션 요약 프롬프트 수정
        prompt = f"""
다음은 뉴스 기사의 일부 문단이다. 이 문단의 **핵심 사실(육하원칙)**과 **주요 주장**을 간결하게 요약해라.

문단({idx+1}):
{chunk}
"""
        summary = await ask_gpt(prompt, max_tokens=400)
        partial_summaries.append(summary)

    merged = "\n".join(partial_summaries)

    # 2. 전체 요약 프롬프트 수정
    final_prompt = f"""
다음은 여러 섹션의 요약문을 결합한 것이다. 이 내용을 **뉴스 기사의 형식**에 맞춰 다음 요소를 포함하여 통합 요약해라.

내용:
{merged}

출력 형식:
1.  **제목 (Headline):** 뉴스 기사의 핵심을 담은 한 문장 제목.
2.  **본문 (Summary):** 누가, 언제, 어디서, 무엇을, 왜, 어떻게 했는지(육하원칙)를 포함하는 2~3문단의 통합 요약.
"""
    final_summary = await ask_gpt(final_prompt, max_tokens=500)
    return final_summary.strip()

# QA 에이전트 (프롬프트 규칙 강화)
async def qa_on_document(summary: str, question: str) -> str:
    prompt = f"""
다음은 뉴스 기사의 요약이다. 이 요약 내의 정보만 사용하여 질문에 답해라.

요약:
{summary}

질문:
{question}

규칙:
- **정보 출처 명확화:** 질문에 대한 답을 요약 내에서 찾아라.
- **추론 금지:** 요약문에 없는 내용은 절대 추론하여 답하지 말 것.
- **답변 불가 시:** 없으면 "뉴스 요약에 해당 정보가 명시되어 있지 않습니다."라고 답해라.
"""
    return (await ask_gpt(prompt, max_tokens=300)).strip()

# 감성 분석 + 키포인트 에이전트 (뉴스에 맞게 키포인트 정의 변경)
async def analyze_opinions(summary: str) -> dict:
    prompt = f"""
다음은 뉴스 기사 요약이다. 이 요약에 대해 **감성 분석**과 **핵심 인물/기관 및 사안** 추출을 수행해라.

요약:
{summary}

출력 형식(JSON):
{{
    "sentiment": "positive | negative | neutral | mixed",
    "key_actors": ["주요 인물 또는 기관1", "주요 인물 또는 기관2", ... 최대 3개],
    "key_issues": ["핵심 사안/쟁점1", "핵심 사안/쟁점2", ... 최대 3개]
}}
"""
    raw = await ask_gpt(prompt, max_tokens=300)

    import json
    try:
        # JSON 파싱 실패를 대비하여 기본값 구조를 변경 (key_points -> key_actors, key_issues)
        result = json.loads(raw)
        # 키 이름이 정확히 일치하지 않을 경우를 대비하여 처리 (선택적)
        if 'key_points' in result:
             result['key_issues'] = result.pop('key_points')
        return result
    except:
        return {"sentiment": "unknown", "key_actors": [], "key_issues": []}

@pdf_analyzer_router.post("/analyze")
async def analyze_document(
        file_url: str = Form(...),
        question: str = Form(...),
        user_id: int = Depends(get_current_user)
):
    try:
        content = download_s3_file(file_url)
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

def download_s3_file(file_url: str) -> bytes:
    parsed = urlparse(file_url)
    bucket_name = parsed.netloc.split('.')[0]
    object_key = parsed.path.lstrip('/')

    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read()
        return content
    except NoCredentialsError:
        raise HTTPException(500, "AWS credentials not available.")
    except s3.exceptions.NoSuchKey:
        raise HTTPException(404, "File not found in S3.")