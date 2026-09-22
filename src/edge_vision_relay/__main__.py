from .api import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("edge_vision_relay.__main__:app", host="0.0.0.0", port=8080)
