import os
os.system("gunicorn -w 4 api:app")
