from fastapi import FastAPI

app = FastAPI(title="Manga Translator API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
