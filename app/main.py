#!/usr/bin/env python3

from flask import Flask
app = Flask(__name__)

@app.route("/")
def handle_index():
    return "hello"

@app.route("/healthcheck")
def handle_healthcheck():
    return "ok"

@app.route("/unlock", methods=["POST"])
def handle_unlock():
    return "ok"


def main():
    app.app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()

