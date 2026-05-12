from fastapi import FastAPI

app = FastAPI(title="crypto-tracker")


@app.get("/health")
def health():
    return {"status": "ok"}
