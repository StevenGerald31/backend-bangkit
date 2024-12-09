from app import create_app
import os
from flask_cors import CORS

app = create_app()
CORS(app)


# get env variables 
app.config['DB_HOST'] = os.getenv('DB_HOST')
app.config['DB_USER'] = os.getenv('DB_USER')
app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD')
app.config['DB_NAME'] = os.getenv('DB_NAME')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
