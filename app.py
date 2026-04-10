from flask import Flask


app = Flask(__name__)

@app.route('/')
def hello():
    return 'This is home page!'

@app.route('/health')
def health():
    return 'OK'

@app.route('/data')
def data():
    return 'This is a test API!'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')