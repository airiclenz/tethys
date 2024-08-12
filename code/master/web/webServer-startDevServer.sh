
VENV_NAME="env_tethys"

source ../$VENV_NAME/bin/activate

python3 manage.py runserver 0.0.0.0:8000
