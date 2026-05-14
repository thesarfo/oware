import os

import uvicorn


def main() -> None:
  uvicorn.run(
    "oware.server.app:app",
    host=os.environ.get("OWARE_HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", os.environ.get("OWARE_PORT", "8000"))),
    reload=os.environ.get("OWARE_RELOAD", "0") == "1",
  )


if __name__ == "__main__":
  main()
