import os
from dotenv import load_dotenv

from config.database.session import Base, engine

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from documents.adapter.input.web.documents_router import documents_router
from social_oauth.adapter.input.web.google_oauth2_router import authentication_router


app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # 정확한 origin만 허용
    allow_credentials=True,      # 쿠키 허용
    allow_methods=["*"],         # 모든 HTTP 메서드 허용
    allow_headers=["*"],         # 모든 헤더 허용
)

app.include_router(authentication_router, prefix="/authentication")
app.include_router(documents_router, prefix="/documents")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST")
    port = int(os.getenv("APP_PORT"))
    Base.metadata.create_all(bind=engine)
    uvicorn.run(app, host=host, port=port)