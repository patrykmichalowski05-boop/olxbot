from app_v2 import create_app

app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8089, debug=False)
