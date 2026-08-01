
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

[200~python manage.py migrate
python manage.py migrate

