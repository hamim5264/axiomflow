from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/receive")
async def receive(req: Request):
    try:
        data = await req.json()
    except Exception:
        data = {}

    print("📩 RECEIVED WEBHOOK:")
    print(data)

    return {
        "status": "ok",
        "received": data
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)
