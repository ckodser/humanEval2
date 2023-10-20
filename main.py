from webapp import create_app

app = create_app()


# gunicorn -c gunicorn.conf.py main:app


def main():
   app.run(debug=False, host="0.0.0.0", port=5002)


if __name__ == "__main__":
   main()
